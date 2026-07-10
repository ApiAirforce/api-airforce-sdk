# api-airforce/sdk (PHP)

Official PHP SDK for the [api.airforce](https://api.airforce) AI gateway — one
OpenAI-compatible API in front of many model providers. cURL-based, no runtime
dependencies (just `ext-curl` + `ext-json`), PHP 8.1+.

## Install

The package is **not yet published to Packagist**. Install it straight from GitHub with a
Composer [path repository](https://getcomposer.org/doc/05-repositories.md#path):

```bash
git clone https://github.com/ApiAirforce/api-airforce-sdk.git
composer config repositories.airforce path api-airforce-sdk/php
composer require api-airforce/sdk:@dev
```

Or skip Composer entirely — the SDK has no runtime dependencies (just `ext-curl` +
`ext-json`, PHP 8.1+), so a PSR-4 autoloader mapping `Airforce\` to
`api-airforce-sdk/php/src/` is all you need. Once published:
`composer require api-airforce/sdk`.

## Quick start

```php
use Airforce\Client;

$client = new Client(apiKey: 'sk-air-...'); // or AIRFORCE_API_KEY env

$res = $client->chat->create([
    'model' => 'claude-opus-4.8',
    'messages' => [
        ['role' => 'user', 'content' => 'Write a haiku about airplanes.'],
    ],
]);

echo $res['choices'][0]['message']['content'];
```

Request bodies are plain arrays; responses are decoded JSON (associative arrays).

## Streaming

```php
$stream = $client->chat->createStream([
    'model' => 'claude-opus-4.8',
    'messages' => [['role' => 'user', 'content' => 'Count to five.']],
]);
foreach ($stream as $chunk) {
    echo $chunk['choices'][0]['delta']['content'] ?? '';
}
```

## Fallback models

```php
$client->chat->create([
    'model' => 'claude-opus-4.8',
    'models' => ['claude-opus-4.8', 'gpt-5.4', 'gemini-2.5-pro'], // first healthy one wins
    'messages' => [['role' => 'user', 'content' => 'hi']],
]);
```

## Reasoning output

By default, reasoning models return their chain-of-thought inline in `content`, wrapped in
`<think>…</think>`. The optional `reasoning` request field reshapes that server-side (it is
never forwarded upstream):

```php
$res = $client->chat->create([
    'model' => 'deepseek-r1',
    'messages' => [['role' => 'user', 'content' => 'Why is the sky blue?']],
    'reasoning' => ['format' => 'separate'], // move it to message.reasoning / delta.reasoning
    // 'reasoning' => ['exclude' => true],   // …or drop it from the response entirely
]);
echo $res['choices'][0]['message']['reasoning']; // the chain-of-thought
echo $res['choices'][0]['message']['content'];   // the clean answer
```

## Embeddings

```php
$emb = $client->embeddings->create([
    'model' => 'embed-1',
    'input' => ['first text', 'second text'], // string | string[] | token arrays
]);
$vector = $emb['data'][0]['embedding'];
```

Billed on input tokens only; no streaming.

## Media

```php
// Image
$img = $client->images->generate(['model' => 'image-1', 'prompt' => 'a red biplane']);

// Text-to-speech → bytes
$audio = $client->audio->speech([
    'model' => 'eleven-v3', 'voice' => '21m00Tcm4TlvDq8ikWAM', 'input' => 'Cleared for takeoff.',
]);
file_put_contents('out.mp3', $audio);

// Video (async — poll until done)
$video = $client->video->generateAndWait(['model' => 'veo-3', 'prompt' => 'a paper plane over a city']);
echo $video['result_url'];

// 3D (async — poll until done, then download the artifact)
$task = $client->threeD->generateAndWait([
    'model' => '3d-1',
    'image_urls' => ['https://example.com/chair.jpg'],
    'resolution' => 'medium',
]);
file_put_contents('model.glb', $client->threeD->content($task['task_id']));
```

3D tasks and their artifacts expire after 24 h; credits are only deducted once a worker
picks the task up, and failures are refunded.

## Account, keys & billing

Account/billing endpoints use a **session token** (JWT). Logging in adopts it
automatically:

```php
$client->auth->login('username', 'password', 'captcha_token');
$me = $client->account->me();
echo "balance (cents): {$me['balance']}";

$key = $client->keys->create(['label' => 'ci', 'rpm_limit' => 60]);
```

You can also pass a token: `new Client(sessionToken: $jwt)` or
`$client->setSessionToken($jwt)`.

Per-user routing preferences (API-key authenticated) live on `account` too:
`setRoutingCategoryPrefs()`, `setChannelOrderPrefs()`, `get`/`setCustomCategories()`, and
custom provider models via `createCustomModel()` / `updateCustomModel()` /
`deleteCustomModel()`.

### Account closure

```php
$client->account->closeAccount('password', totpCode: '123456'); // soft-close (idempotent)
// ...within the 14-day grace window:
$client->auth->reactivate('former-email@example.com', 'password');
```

## Organizations

Team self-service under `/api/org/*` (session token; the org context is implicit via your
membership):

```php
['org' => $org, 'role' => $role] = $client->org->get();
$members = $client->org->members();                                  // owner/admin
$invite = $client->org->createInvite('teammate@example.com');        // 7-day expiry
$key = $client->org->createKey(['member_user_id' => $members[0]['user_id'], 'label' => 'ci']);
$usage = $client->org->usage(from: time() - 86400 * 7);              // cents
```

## Notifications

```php
$prefs = $client->notifications->getPrefs();
$client->notifications->updatePrefs(['digest_frequency' => 'daily']);

$feed = $client->notifications->list(limit: 10); // ['items' => [...], 'unread' => n]
$client->notifications->markAllRead();

// Link a delivery channel (the verification code arrives through the channel itself)
$client->notifications->linkChannel('email', 'me@example.com');
$client->notifications->verifyChannel('email', '123456');
```

## OAuth (third-party integrators)

```php
use Airforce\Resources\OAuth;

$pkce = OAuth::createPkcePair();
$url = $client->oauth->authorizeUrl(
    clientId: 'airforce_...',
    redirectUri: 'https://app.example.com/callback',
    scope: ['profile', 'chat'],
    codeChallenge: $pkce['challenge'],
);
// ...after the redirect:
$token = $client->oauth->exchangeToken([
    'code' => $code,
    'redirect_uri' => 'https://app.example.com/callback',
    'client_id' => 'airforce_...',
    'code_verifier' => $pkce['verifier'],
]);
```

## Errors

Failures throw an `Airforce\AirforceException`:

```php
use Airforce\AirforceException;

try {
    $client->chat->create($request);
} catch (AirforceException $e) {
    if ($e->isRateLimited()) {
        echo "retry after {$e->retryAfter}";
    }
}
```

`MissingCredentialException`, `ApiConnectionException` and `ApiTimeoutException` cover the
non-HTTP failure modes.

## Configuration

```php
new Client(
    apiKey: 'sk-air-...',
    sessionToken: '...',          // for account/billing endpoints
    baseUrl: 'https://api.airforce',
    timeout: 60.0,
    maxRetries: 2,                // retried on 429 / 5xx / network errors
    defaultHeaders: ['x-custom' => 'value'],
);
```

## License

MIT
