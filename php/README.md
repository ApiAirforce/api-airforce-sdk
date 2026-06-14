# api-airforce/sdk (PHP)

Official PHP SDK for the [api.airforce](https://api.airforce) AI gateway — one
OpenAI-compatible API in front of many model providers. cURL-based, no runtime
dependencies (just `ext-curl` + `ext-json`), PHP 8.1+.

## Install

```bash
composer require api-airforce/sdk
```

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
```

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
