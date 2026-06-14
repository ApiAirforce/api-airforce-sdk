<?php

declare(strict_types=1);

namespace Airforce;

final class Sse
{
    /**
     * Parse a Server-Sent Events chunk iterable into decoded JSON events.
     *
     * @param iterable<string> $chunks
     * @return \Generator<int, mixed>
     */
    public static function parse(iterable $chunks): \Generator
    {
        $buffer = '';
        $data = [];

        foreach ($chunks as $chunk) {
            $buffer .= str_replace(["\r\n", "\r"], "\n", $chunk);
            while (($pos = strpos($buffer, "\n")) !== false) {
                $line = substr($buffer, 0, $pos);
                $buffer = substr($buffer, $pos + 1);

                if ($line === '') {
                    if ($data === []) {
                        continue;
                    }
                    $payload = implode("\n", $data);
                    $data = [];
                    if ($payload === '[DONE]') {
                        return;
                    }
                    yield json_decode($payload, true);
                } elseif (str_starts_with($line, ':')) {
                    // comment / keep-alive
                } elseif (str_starts_with($line, 'data:')) {
                    $value = substr($line, 5);
                    if (str_starts_with($value, ' ')) {
                        $value = substr($value, 1);
                    }
                    $data[] = $value;
                }
            }
        }

        if ($data !== []) {
            $payload = implode("\n", $data);
            if ($payload !== '[DONE]') {
                yield json_decode($payload, true);
            }
        }
    }
}
