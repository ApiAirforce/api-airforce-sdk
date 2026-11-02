package airforce

import (
	"context"
	"encoding/json"
)

// RerankParams configures a POST /v1/rerank request. Documents are plain
// strings or objects with a "text" field (at most 1,000), forwarded unchanged.
// The optional fields are pointers so that an explicit false or 0 is sent as
// given; nil leaves the field out.
type RerankParams struct {
	Model           string `json:"model"`
	Query           string `json:"query"`
	Documents       []any  `json:"documents"`
	TopN            *int   `json:"top_n,omitempty"`
	ReturnDocuments *bool  `json:"return_documents,omitempty"`
	MaxChunksPerDoc *int   `json:"max_chunks_per_doc,omitempty"`
	OverlapTokens   *int   `json:"overlap_tokens,omitempty"`
	User            string `json:"user,omitempty"`
}

// RerankResult is one scored document. Index points into the request's
// Documents slice.
type RerankResult struct {
	Index          int     `json:"index"`
	RelevanceScore float64 `json:"relevance_score"`
	Document       any     `json:"document,omitempty"`
}

// RerankResponse is the model provider's body. Results and Usage cover the
// common shape; Raw keeps the body exactly as received, for models that name
// their fields differently.
type RerankResponse struct {
	Results []RerankResult  `json:"results"`
	Usage   map[string]any  `json:"usage,omitempty"`
	Raw     json.RawMessage `json:"-"`
}

// UnmarshalJSON decodes the common fields and keeps the raw body in Raw.
func (r *RerankResponse) UnmarshalJSON(b []byte) error {
	type plain RerankResponse
	var p plain
	if err := json.Unmarshal(b, &p); err != nil {
		return err
	}
	*r = RerankResponse(p)
	r.Raw = append(json.RawMessage(nil), b...)
	return nil
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
