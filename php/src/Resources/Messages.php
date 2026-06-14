<?php

declare(strict_types=1);

namespace Airforce\Resources;

use Airforce\Transport;

/** Anthropic-compatible messages — POST /v1/messages. */
final class Messages
{
    public function __construct(private Transport $t)
    {
    }

    /** @param array<string,mixed> $request */
    public function create(array $request): mixed
    {
        return $this->t->post('/v1/messages', 'api_key', [...$request, 'stream' => false]);
    }

    /** @param array<string,mixed> $request @return \Generator<int,mixed> */
    public function createStream(array $request): \Generator
    {
        return $this->t->stream('POST', '/v1/messages', 'api_key', [...$request, 'stream' => true]);
    }

    /** @param array<string,mixed> $request */
    public function countTokens(array $request): mixed
    {
        return $this->t->post('/v1/messages/count_tokens', 'api_key', $request);
    }
}
