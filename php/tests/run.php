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

echo "\n{$passed} passed, {$failed} failed\n";
exit($failed === 0 ? 0 : 1);
