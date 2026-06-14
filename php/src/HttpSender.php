<?php

declare(strict_types=1);

namespace Airforce;

/**
 * Low-level HTTP sender. The default is {@see CurlSender}; tests inject a mock.
 */
interface HttpSender
{
    /**
     * Perform one HTTP request.
     *
     * @param array<string, string> $headers
     * @return array{status:int, headers:array<string,string>, body:string|iterable<string>}
     *         For non-streaming the body is a string; for streaming it is an iterable of chunks.
     * @throws ApiConnectionException|ApiTimeoutException on transport failure (no response).
     */
    public function send(string $method, string $url, array $headers, ?string $body, bool $stream): array;
}
