<?php

declare(strict_types=1);

namespace Airforce\Resources;

use Airforce\Transport;

/** Rerank — POST /v1/rerank. */
final class Rerank
{
    public function __construct(private Transport $t)
    {
    }

    /**
     * Score documents against a query. No streaming; billed on input tokens only. Returns the
     * model provider's body as received, typically `{results: [{index, relevance_score, document?}], usage}`.
     *
     * @param array<string,mixed> $request `{model, query, documents ((string | {text, ...})[], at most 1,000), top_n?, return_documents?, max_chunks_per_doc?, overlap_tokens?, user?}`
     */
    public function create(array $request): mixed
    {
        return $this->t->post('/v1/rerank', 'api_key', $request);
    }
}
