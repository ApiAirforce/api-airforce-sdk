<?php

declare(strict_types=1);

namespace Airforce\Resources;

use Airforce\Transport;

/** Embeddings — POST /v1/embeddings. */
final class Embeddings
{
    public function __construct(private Transport $t)
    {
    }

    /**
     * Create embeddings for the given input. No streaming; billed on input tokens only.
     *
     * @param array<string,mixed> $request `{model, input (string | string[] | int[] | int[][]), encoding_format?, dimensions?, user?}`
     */
    public function create(array $request): mixed
    {
        return $this->t->post('/v1/embeddings', 'api_key', $request);
    }
}
