package airforce

import "context"

// RerankParams configures a POST /v1/rerank request. Documents are plain
// strings or objects with a "text" field (at most 1,000), forwarded unchanged.
type RerankParams struct {
	Model           string `json:"model"`
	Query           string `json:"query"`
	Documents       []any  `json:"documents"`
	TopN            int    `json:"top_n,omitempty"`
	ReturnDocuments bool   `json:"return_documents,omitempty"`
	MaxChunksPerDoc int    `json:"max_chunks_per_doc,omitempty"`
	OverlapTokens   int    `json:"overlap_tokens,omitempty"`
	User            string `json:"user,omitempty"`
}

// RerankResult is one scored document. Index points into the request's
// Documents slice.
type RerankResult struct {
	Index          int     `json:"index"`
	RelevanceScore float64 `json:"relevance_score"`
	Document       any     `json:"document,omitempty"`
}

// RerankResponse is the model provider's body as received. Usage is kept as a
// map because a few models name its fields differently.
type RerankResponse struct {
	Results []RerankResult `json:"results"`
	Usage   map[string]any `json:"usage,omitempty"`
}

// RerankService accesses /v1/rerank.
type RerankService struct{ client *Client }

// Create scores the documents against the query and returns them ordered by
// relevance. Billed on input tokens only; no streaming variant exists.
func (s *RerankService) Create(ctx context.Context, params RerankParams) (*RerankResponse, error) {
	var out RerankResponse
	err := s.client.postJSON(ctx, "/v1/rerank", "api_key", params, &out)
	return &out, err
}
