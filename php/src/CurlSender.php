<?php

declare(strict_types=1);

namespace Airforce;

/**
 * Default {@see HttpSender}: cURL for normal requests, PHP streams for SSE.
 */
final class CurlSender implements HttpSender
{
    public function __construct(private float $timeout = 60.0)
    {
    }

    public function send(string $method, string $url, array $headers, ?string $body, bool $stream): array
    {
        if ($stream) {
            return $this->stream($method, $url, $headers, $body);
        }

        $ch = curl_init($url);
        $headerLines = [];
        foreach ($headers as $name => $value) {
            $headerLines[] = "{$name}: {$value}";
        }
        $respHeaders = [];
        curl_setopt_array($ch, [
            CURLOPT_CUSTOMREQUEST => strtoupper($method),
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_HTTPHEADER => $headerLines,
            CURLOPT_TIMEOUT => (int) ceil($this->timeout),
            CURLOPT_CONNECTTIMEOUT => (int) ceil($this->timeout),
            CURLOPT_HEADERFUNCTION => function ($ch, string $line) use (&$respHeaders): int {
                $parts = explode(':', $line, 2);
                if (count($parts) === 2) {
                    $key = strtolower(trim($parts[0]));
                    $val = trim($parts[1]);
                    // Preserve multiple Set-Cookie headers by concatenating.
                    $respHeaders[$key] = isset($respHeaders[$key]) ? $respHeaders[$key] . "\n" . $val : $val;
                }
                return strlen($line);
            },
        ]);
        if ($body !== null) {
            curl_setopt($ch, CURLOPT_POSTFIELDS, $body);
        }

        $result = curl_exec($ch);
        if ($result === false) {
            $errno = curl_errno($ch);
            $error = curl_error($ch);
            curl_close($ch);
            if ($errno === CURLE_OPERATION_TIMEDOUT) {
                throw new ApiTimeoutException("request timed out: {$error}");
            }
            throw new ApiConnectionException("request failed: {$error}");
        }
        $status = (int) curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);

        return ['status' => $status, 'headers' => $respHeaders, 'body' => (string) $result];
    }

    /** @return array{status:int, headers:array<string,string>, body:iterable<string>} */
    private function stream(string $method, string $url, array $headers, ?string $body): array
    {
        $headerLines = [];
        foreach ($headers as $name => $value) {
            $headerLines[] = "{$name}: {$value}";
        }
        $opts = ['http' => [
            'method' => strtoupper($method),
            'header' => implode("\r\n", $headerLines),
            'ignore_errors' => true,
            'timeout' => $this->timeout,
        ]];
        if ($body !== null) {
            $opts['http']['content'] = $body;
        }
        $context = stream_context_create($opts);
        $fp = @fopen($url, 'r', false, $context);
        if ($fp === false) {
            throw new ApiConnectionException("failed to open stream to {$url}");
        }
        // $http_response_header is populated by fopen() in the local scope.
        $status = 0;
        $respHeaders = [];
        foreach ($http_response_header ?? [] as $i => $line) {
            if ($i === 0 && preg_match('#HTTP/\S+\s+(\d+)#', $line, $m)) {
                $status = (int) $m[1];
            } elseif (str_contains($line, ':')) {
                [$k, $v] = explode(':', $line, 2);
                $respHeaders[strtolower(trim($k))] = trim($v);
            }
        }

        $generator = (static function () use ($fp): \Generator {
            try {
                while (!feof($fp)) {
                    $line = fgets($fp);
                    if ($line === false) {
                        break;
                    }
                    yield $line;
                }
            } finally {
                fclose($fp);
            }
        })();

        return ['status' => $status, 'headers' => $respHeaders, 'body' => $generator];
    }
}
