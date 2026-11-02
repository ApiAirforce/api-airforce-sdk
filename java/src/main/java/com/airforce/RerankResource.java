package com.airforce;

import com.fasterxml.jackson.databind.JsonNode;
import java.util.Map;

/** Rerank — {@code POST /v1/rerank}. */
public final class RerankResource extends Resource {

  RerankResource(Transport transport) {
    super(transport);
  }

  /**
   * Score documents against a query. {@code params} must include {@code model}, {@code query}
   * and {@code documents} (strings or objects with a {@code text} field, at most 1,000);
   * optional keys: top_n, return_documents, max_chunks_per_doc, overlap_tokens, user. Billed on
   * input tokens only; no streaming. Returns the model provider's body as received, typically
   * {@code {results:[{index, relevance_score, document?}], usage}}.
   */
  public JsonNode create(Map<String, Object> params) {
    return transport.post("/v1/rerank", "api_key", params);
  }
}
