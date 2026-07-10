<?php

declare(strict_types=1);

namespace Airforce\Resources;

use Airforce\Transport;

/**
 * Chat completions — POST /v1/chat/completions.
 *
 * Requests are plain arrays and passed through as-is. Notable optional fields beyond the
 * OpenAI baseline:
 * - `models` (string[], ≤3): fallback list — the gateway tries each model's provider
 *   chain in order and bills only the one that answers.
 * - `reasoning` (`{format?: 'separate'|'inline', exclude?: bool}`): response-side shaping
 *   of reasoning output, consumed server-side (never forwarded upstream). `'separate'`
 *   moves reasoning into `message.reasoning` / `delta.reasoning` and strips it from
 *   `content`; `exclude: true` drops reasoning from the response entirely; absent or
 *   `'inline'` keeps reasoning wrapped in `<think>…</think>` inside `content`.
 */
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
