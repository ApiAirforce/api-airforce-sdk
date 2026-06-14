<?php

declare(strict_types=1);

namespace Airforce\Resources;

use Airforce\Transport;

/** Chat completions — POST /v1/chat/completions. */
final class Chat
{
    public function __construct(private Transport $t)
    {
    }

    /** @param array<string,mixed> $request */
    public function create(array $request): mixed
    {
        return $this->t->post('/v1/chat/completions', 'api_key', [...$request, 'stream' => false]);
    }

    /** @param array<string,mixed> $request @return \Generator<int,mixed> */
    public function createStream(array $request): \Generator
    {
        return $this->t->stream('POST', '/v1/chat/completions', 'api_key', [...$request, 'stream' => true]);
    }
}
