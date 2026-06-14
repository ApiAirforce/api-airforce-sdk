<?php

declare(strict_types=1);

namespace Airforce\Resources;

use Airforce\Transport;

/** Google Gemini-compatible generation — POST /v1beta/models/{model}:{method}. */
final class Gemini
{
    public function __construct(private Transport $t)
    {
    }

    /** @param array<string,mixed> $request */
    public function generateContent(string $model, array $request): mixed
    {
        return $this->t->post('/v1beta/models/' . rawurlencode($model) . ':generateContent', 'api_key', $request);
    }

    /** @param array<string,mixed> $request @return \Generator<int,mixed> */
    public function streamGenerateContent(string $model, array $request): \Generator
    {
        return $this->t->stream('POST', '/v1beta/models/' . rawurlencode($model) . ':streamGenerateContent', 'api_key', $request);
    }
}
