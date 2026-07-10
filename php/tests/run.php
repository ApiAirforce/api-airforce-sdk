<?php

declare(strict_types=1);

use Airforce\AirforceException;
use Airforce\Client;
use Airforce\HttpSender;
use Airforce\MissingCredentialException;

// Minimal PSR-4 autoloader (so the suite runs without Composer).
spl_autoload_register(static function (string $class): void {
    $prefix = 'Airforce\\';
    if (str_starts_with($class, $prefix)) {
        $file = __DIR__ . '/../src/' . str_replace('\\', '/', substr($class, strlen($prefix))) . '.php';
        if (is_file($file)) {
            require $file;
        }
    }
});

/** A mock sender returning canned responses; records requests. */
final class MockSender implements HttpSender
{
    /** @var list<array{method:string,url:string,headers:array,body:?string,stream:bool}> */
    public array $requests = [];
    /** @var callable */
    private $handler;

    public function __construct(callable $handler)
    {
        $this->handler = $handler;
    }

    public function send(string $method, string $url, array $headers, ?string $body, bool $stream): array
    {
        $this->requests[] = compact('method', 'url', 'headers', 'body', 'stream');
        return ($this->handler)();
    }
}

// --- tiny test framework -----------------------------------------------------

$passed = 0;
$failed = 0;
function ok(bool $cond, string $msg): void
{
    global $passed, $failed;
    if ($cond) {
        $passed++;
    } else {
        $failed++;
        fwrite(STDERR, "FAIL: {$msg}\n");
    }
}
function eq(mixed $actual, mixed $expected, string $msg): void
{
    ok($actual === $expected, $msg . ' (expected ' . var_export($expected, true) . ', got ' . var_export($actual, true) . ')');
}

/** @return array{status:int,headers:array,body:string} */
function jsonResp(int $status, string $body, array $headers = []): array
{
    return ['status' => $status, 'headers' => ['content-type' => 'application/json'] + $headers, 'body' => $body];
}
function sseResp(string $sse): array
{
    return ['status' => 200, 'headers' => ['content-type' => 'text/event-stream'], 'body' => (static function () use ($sse) {
        yield $sse;
    })()];
}

const COMPLETION = '{"id":"cmpl_1","object":"chat.completion","created":0,"model":"claude-opus-4.8",'
    . '"choices":[{"index":0,"message":{"role":"assistant","content":"hi"},"finish_reason":"stop"}]}';

// 1. chat.create sends Bearer + parses
$mock = new MockSender(static fn () => jsonResp(200, COMPLETION));
$client = new Client(apiKey: 'sk-air-test', baseUrl: 'https://api.airforce', sender: $mock);
$res = $client->chat->create(['model' => 'claude-opus-4.8', 'messages' => []]);
eq($res['choices'][0]['message']['content'], 'hi', 'chat content');
eq($mock->requests[0]['headers']['authorization'] ?? null, 'Bearer sk-air-test', 'auth header');
eq(parse_url($mock->requests[0]['url'], PHP_URL_PATH), '/v1/chat/completions', 'request path');

// 2. missing api key throws
$mock = new MockSender(static fn () => jsonResp(200, '{}'));
$client = new Client(baseUrl: 'https://api.airforce', sender: $mock);
$threw = false;
try {
    $client->chat->create(['model' => 'm', 'messages' => []]);
} catch (MissingCredentialException) {
    $threw = true;
}
ok($threw, 'missing api key throws MissingCredentialException');

// 3. session endpoint requires a session token (no api-key fallback)
$mock = new MockSender(static fn () => jsonResp(200, '{}'));
$client = new Client(apiKey: 'sk-air-test', baseUrl: 'https://api.airforce', sender: $mock);
$threw = false;
try {
    $client->account->me();
} catch (MissingCredentialException) {
    $threw = true;
}
ok($threw, 'session endpoint requires session token');

// 4. public endpoint has no auth
$mock = new MockSender(static fn () => jsonResp(200, '{"object":"list","data":[]}'));
$client = new Client(apiKey: 'sk-air-test', baseUrl: 'https://api.airforce', sender: $mock);
$client->models->list();
ok(!isset($mock->requests[0]['headers']['authorization']), 'public endpoint sends no auth');

// 5. retries on 429 then succeeds
$calls = 0;
$mock = new MockSender(static function () use (&$calls) {
    $calls++;
    return $calls === 1 ? jsonResp(429, '{"error":"slow"}', ['retry-after' => '0']) : jsonResp(200, COMPLETION);
});
$client = new Client(apiKey: 'sk-air-test', baseUrl: 'https://api.airforce', sender: $mock);
$res = $client->chat->create(['model' => 'm', 'messages' => []]);
eq($res['id'], 'cmpl_1', 'retry result id');
eq($calls, 2, 'retry made 2 calls');

// 6. error mapping
$mock = new MockSender(static fn () => jsonResp(402, '{"error":{"message":"no balance","code":"insufficient_balance"}}'));
$client = new Client(apiKey: 'sk-air-test', baseUrl: 'https://api.airforce', sender: $mock);
$err = null;
try {
    $client->chat->create(['model' => 'm', 'messages' => []]);
} catch (AirforceException $e) {
    $err = $e;
}
ok($err !== null && $err->status === 402 && $err->isInsufficientBalance() && $err->code() === 'insufficient_balance', 'error mapping 402');

// 7. streaming assembles content
$sse = "data: {\"choices\":[{\"index\":0,\"delta\":{\"content\":\"he\"},\"finish_reason\":null}]}\n\n"
    . "data: {\"choices\":[{\"index\":0,\"delta\":{\"content\":\"llo\"},\"finish_reason\":\"stop\"}]}\n\n"
    . "data: [DONE]\n\n";
$mock = new MockSender(static fn () => sseResp($sse));
$client = new Client(apiKey: 'sk-air-test', baseUrl: 'https://api.airforce', sender: $mock);
$text = '';
foreach ($client->chat->createStream(['model' => 'm', 'messages' => []]) as $chunk) {
    $text .= $chunk['choices'][0]['delta']['content'] ?? '';
}
eq($text, 'hello', 'streaming content');

// 8. embeddings sends api-key auth + parses the OpenAI list shape
$mock = new MockSender(static fn () => jsonResp(200, '{"object":"list","data":[{"object":"embedding","index":0,'
    . '"embedding":[0.1,0.2]}],"model":"embed-1","usage":{"prompt_tokens":2,"total_tokens":2}}'));
$client = new Client(apiKey: 'sk-air-test', baseUrl: 'https://api.airforce', sender: $mock);
$res = $client->embeddings->create(['model' => 'embed-1', 'input' => 'hello']);
eq($res['data'][0]['embedding'][1], 0.2, 'embeddings vector');
eq($res['usage']['prompt_tokens'], 2, 'embeddings usage');
eq(parse_url($mock->requests[0]['url'], PHP_URL_PATH), '/v1/embeddings', 'embeddings path');
eq($mock->requests[0]['headers']['authorization'] ?? null, 'Bearer sk-air-test', 'embeddings auth header');

// 9. org members list uses the session token and unwraps `members`
$mock = new MockSender(static fn () => jsonResp(200, '{"members":[{"user_id":"u1","role":"owner","status":"active","joined_at":0}]}'));
$client = new Client(sessionToken: 'jwt-test', baseUrl: 'https://api.airforce', sender: $mock);
$members = $client->org->members();
eq($members[0]['user_id'], 'u1', 'org members unwrap');
eq($mock->requests[0]['method'], 'GET', 'org members method');
eq(parse_url($mock->requests[0]['url'], PHP_URL_PATH), '/api/org/members', 'org members path');
eq($mock->requests[0]['headers']['authorization'] ?? null, 'Bearer jwt-test', 'org session auth');

// 10. notifications list forwards paging query params
$mock = new MockSender(static fn () => jsonResp(200, '{"items":[{"id":"n1","kind":"price_drop"}],"unread":3}'));
$client = new Client(sessionToken: 'jwt-test', baseUrl: 'https://api.airforce', sender: $mock);
$res = $client->notifications->list(limit: 10, before: '2026-01-01T00:00:00Z');
eq($res['unread'], 3, 'notifications unread');
eq($res['items'][0]['id'], 'n1', 'notifications item id');
eq(parse_url($mock->requests[0]['url'], PHP_URL_PATH), '/api/me/notifications', 'notifications path');
parse_str((string) parse_url($mock->requests[0]['url'], PHP_URL_QUERY), $q);
eq($q['limit'] ?? null, '10', 'notifications limit query');
eq($q['before'] ?? null, '2026-01-01T00:00:00Z', 'notifications before query');

// 11. account close sends DELETE with the re-auth body
$mock = new MockSender(static fn () => jsonResp(200, '{"closed":true}'));
$client = new Client(sessionToken: 'jwt-test', baseUrl: 'https://api.airforce', sender: $mock);
$res = $client->account->closeAccount('hunter2', totpCode: '123456', forfeitBalanceAck: true);
eq($res['closed'], true, 'account close result');
eq($mock->requests[0]['method'], 'DELETE', 'account close method');
eq(parse_url($mock->requests[0]['url'], PHP_URL_PATH), '/api/me/account', 'account close path');
$body = json_decode((string) $mock->requests[0]['body'], true);
eq($body['password'] ?? null, 'hunter2', 'account close password');
eq($body['totp_code'] ?? null, '123456', 'account close totp');
eq($body['forfeit_balance_ack'] ?? null, true, 'account close forfeit ack');

// 12. 3d task content returns raw bytes
$glb = "glTF\x02\x00\x00\x00";
$mock = new MockSender(static fn () => ['status' => 200, 'headers' => ['content-type' => 'model/gltf-binary'], 'body' => $glb]);
$client = new Client(apiKey: 'sk-air-test', baseUrl: 'https://api.airforce', sender: $mock);
eq($client->threeD->content('task_1'), $glb, '3d content bytes');
eq(parse_url($mock->requests[0]['url'], PHP_URL_PATH), '/v1/3d/tasks/task_1/content', '3d content path');

echo "\n{$passed} passed, {$failed} failed\n";
exit($failed === 0 ? 0 : 1);
