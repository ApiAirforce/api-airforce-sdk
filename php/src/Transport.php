<?php

declare(strict_types=1);

namespace Airforce;

final class Transport
{
    private const VERSION = '0.0.1';
    // 409 is excluded: a terminal business conflict, not transient.
    private const RETRYABLE = [408, 429, 500, 502, 503, 504];

    /** @param array<string,string> $defaultHeaders */
    public function __construct(
        private HttpSender $sender,
        private ?string $apiKey,
        private ?string $sessionToken,
        public string $baseUrl,
        private int $maxRetries,
        private array $defaultHeaders,
    ) {
    }

    public function setSessionToken(?string $token): void
    {
        $this->sessionToken = $token;
    }

    private function resolveToken(string $auth): ?string
    {
        if ($auth === 'none') {
            return null;
        }
        // Session endpoints require a session JWT — never substitute an API key.
        $token = $auth === 'session' ? $this->sessionToken : ($this->apiKey ?? $this->sessionToken);
        if ($token === null) {
            throw new MissingCredentialException($auth === 'session'
                ? 'This endpoint requires a session token (set sessionToken / auth()->login()).'
                : 'This endpoint requires an API key (set apiKey).');
        }
        return $token;
    }

    /**
     * @param array<string,string>|null $query
     * @param array<string,string>|null $extraHeaders
     * @return array{status:int, headers:array<string,string>, body:string|iterable<string>}
     */
    private function rawSend(
        string $method,
        string $path,
        string $auth,
        ?string $rawBody,
        ?string $contentType,
        ?array $query,
        ?array $extraHeaders,
        bool $stream,
    ): array {
        $token = $this->resolveToken($auth);
        $url = $this->baseUrl . (str_starts_with($path, '/') ? $path : '/' . $path);
        if ($query) {
            $url .= '?' . http_build_query($query);
        }

        $headers = [
            'user-agent' => 'airforce-sdk-php/' . self::VERSION,
            'x-airforce-sdk' => 'php/' . self::VERSION,
            'accept' => $stream ? 'text/event-stream' : 'application/json',
        ] + $this->defaultHeaders;
        if ($token !== null) {
            $headers['authorization'] = 'Bearer ' . $token;
        }
        if ($contentType !== null) {
            $headers['content-type'] = $contentType;
        }
        if ($extraHeaders) {
            $headers = array_merge($headers, $extraHeaders);
        }

        for ($attempt = 0;; $attempt++) {
            try {
                $resp = $this->sender->send($method, $url, $headers, $rawBody, $stream);
            } catch (ApiConnectionException | ApiTimeoutException $e) {
                // A transport error leaves a POST's outcome unknown — retrying could
                // double-charge a billable request. Only retry idempotent methods.
                if ($attempt < $this->maxRetries && strtoupper($method) !== 'POST') {
                    $this->backoff($attempt + 1, null);
                    continue;
                }
                throw $e;
            }

            $status = $resp['status'];
            if ($status < 400) {
                return $resp;
            }
            $retryAfter = $this->retryAfter($resp['headers']);
            if (in_array($status, self::RETRYABLE, true) && $attempt < $this->maxRetries) {
                $this->backoff($attempt + 1, $retryAfter);
                continue;
            }
            $body = is_string($resp['body']) ? $resp['body'] : $this->iterToString($resp['body']);
            throw AirforceException::fromResponse(
                $status,
                $body,
                $resp['headers']['x-request-id'] ?? null,
                $retryAfter ?? 0.0
            );
        }
    }

    /** @param array<string,mixed>|null $body */
    public function requestJson(string $method, string $path, string $auth = 'api_key', ?array $body = null, ?array $query = null, ?array $headers = null): mixed
    {
        $resp = $this->rawSend(
            $method,
            $path,
            $auth,
            $body !== null ? json_encode($body) : null,
            $body !== null ? 'application/json' : null,
            $query,
            $headers,
            false
        );
        $raw = (string) $resp['body'];
        return $raw === '' ? null : json_decode($raw, true);
    }

    /** @param array<string,mixed>|null $body */
    public function requestBytes(string $method, string $path, string $auth, ?array $body = null): string
    {
        $resp = $this->rawSend(
            $method,
            $path,
            $auth,
            $body !== null ? json_encode($body) : null,
            $body !== null ? 'application/json' : null,
            null,
            null,
            false
        );
        return (string) $resp['body'];
    }

    /** @return \Generator<int,mixed> */
    public function stream(string $method, string $path, string $auth, ?array $body = null): \Generator
    {
        $resp = $this->rawSend(
            $method,
            $path,
            $auth,
            $body !== null ? json_encode($body) : null,
            $body !== null ? 'application/json' : null,
            null,
            null,
            true
        );
        yield from Sse::parse($resp['body']);
    }

    /** @return array{0:mixed,1:?string} */
    public function requestJsonCookie(string $path, ?array $body, ?array $headers): array
    {
        $resp = $this->rawSend(
            'POST',
            $path,
            'none',
            $body !== null ? json_encode($body) : null,
            $body !== null ? 'application/json' : null,
            null,
            $headers,
            false
        );
        $cookie = null;
        if (isset($resp['headers']['set-cookie'])
            && preg_match('/airforce_session=([^;\n]+)/', $resp['headers']['set-cookie'], $m)) {
            $cookie = $m[1];
        }
        $raw = (string) $resp['body'];
        return [$raw === '' ? null : json_decode($raw, true), $cookie];
    }

    public function multipart(string $path, string $body, string $contentType, bool $bytes = false): mixed
    {
        $resp = $this->rawSend('POST', $path, 'api_key', $body, $contentType, null, null, false);
        if ($bytes) {
            return (string) $resp['body'];
        }
        $raw = (string) $resp['body'];
        return $raw === '' ? null : json_decode($raw, true);
    }

    /** @param array<string,string> $fields */
    public function form(string $path, array $fields): mixed
    {
        $resp = $this->rawSend('POST', $path, 'none', http_build_query($fields), 'application/x-www-form-urlencoded', null, null, false);
        $raw = (string) $resp['body'];
        return $raw === '' ? null : json_decode($raw, true);
    }

    // --- convenience ---------------------------------------------------------

    public function get(string $path, string $auth, ?array $query = null): mixed
    {
        return $this->requestJson('GET', $path, $auth, null, $query);
    }
    public function post(string $path, string $auth, ?array $body = null): mixed
    {
        return $this->requestJson('POST', $path, $auth, $body);
    }
    public function method(string $m, string $path, string $auth, ?array $body = null): mixed
    {
        return $this->requestJson($m, $path, $auth, $body);
    }
    public function delete(string $path, string $auth): mixed
    {
        return $this->requestJson('DELETE', $path, $auth);
    }
    public function postBytes(string $path, string $auth, array $body): string
    {
        return $this->requestBytes('POST', $path, $auth, $body);
    }
    public function getBytes(string $path, string $auth): string
    {
        return $this->requestBytes('GET', $path, $auth);
    }
    public function getWithHeader(string $path, array $headers): mixed
    {
        return $this->requestJson('GET', $path, 'none', null, null, $headers);
    }

    private function retryAfter(array $headers): ?float
    {
        return isset($headers['retry-after']) && is_numeric($headers['retry-after'])
            ? (float) $headers['retry-after']
            : null;
    }

    private function backoff(int $attempt, ?float $retryAfter): void
    {
        $base = $retryAfter ?? min(2 ** ($attempt - 1), 8);
        $jitter = $base * 0.25 * (mt_rand() / mt_getrandmax());
        usleep((int) (($base + $jitter) * 1_000_000));
    }

    private function iterToString(iterable $it): string
    {
        $out = '';
        foreach ($it as $chunk) {
            $out .= $chunk;
        }
        return $out;
    }
}
