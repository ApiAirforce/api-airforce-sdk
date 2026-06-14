package airforce

import (
	"context"
	"net/http"
	"net/url"
)

// Model is a public model entry. Only commonly used fields are typed; use
// ListRaw for the full, untyped catalog object.
type Model struct {
	ID                     string `json:"id"`
	Object                 string `json:"object"`
	Created                int64  `json:"created"`
	OwnedBy                string `json:"owned_by"`
	SupportsChat           bool   `json:"supports_chat"`
	SupportsImages         bool   `json:"supports_images"`
	Tier                   string `json:"tier"`
	Status                 string `json:"status"`
	MaxTokens              int    `json:"max_tokens"`
	ContextLength          int    `json:"context_length"`
	PricePerMillionTokens  *int   `json:"pricepermilliontokens"`
	OutputPricePerMillion  *int   `json:"output_pricepermilliontokens"`
	PricePerThousandImages *int   `json:"priceperthousandimages"`
	MediaType              string `json:"media_type"`
	Group                  string `json:"group"`
}

// ModelClasses are the playground filter buckets.
type ModelClasses struct {
	Cheapest []string `json:"cheapest"`
	Smartest []string `json:"smartest"`
	Fastest  []string `json:"fastest"`
}

// ModelsService accesses the model catalog.
type ModelsService struct{ client *Client }

func (s *ModelsService) listOptions(channels bool) requestOptions {
	o := requestOptions{auth: "none"}
	if channels {
		o.query = url.Values{"channels": {"1"}}
	}
	return o
}

// List returns the public model list (typed).
func (s *ModelsService) List(ctx context.Context, channels bool) ([]Model, error) {
	var out struct {
		Data []Model `json:"data"`
	}
	if err := s.client.requestJSON(ctx, http.MethodGet, "/v1/models", s.listOptions(channels), &out); err != nil {
		return nil, err
	}
	return out.Data, nil
}

// ListRaw returns the full, untyped model list.
func (s *ModelsService) ListRaw(ctx context.Context, channels bool) ([]map[string]any, error) {
	var out struct {
		Data []map[string]any `json:"data"`
	}
	err := s.client.requestJSON(ctx, http.MethodGet, "/v1/models", s.listOptions(channels), &out)
	return out.Data, err
}

// Detail returns per-model analytics + channel breakdown.
func (s *ModelsService) Detail(ctx context.Context, model string) (map[string]any, error) {
	var out map[string]any
	err := s.client.requestJSON(ctx, http.MethodGet, "/api/models/"+url.PathEscape(model)+"/detail", requestOptions{auth: "none"}, &out)
	return out, err
}

// AllowedParams returns effective parameter bounds for a model.
func (s *ModelsService) AllowedParams(ctx context.Context, model string) (map[string]any, error) {
	var out map[string]any
	err := s.client.requestJSON(ctx, http.MethodGet, "/api/models/"+url.PathEscape(model)+"/allowed-params", requestOptions{auth: "none"}, &out)
	return out, err
}

// Classes returns the cheapest/smartest/fastest playground buckets.
func (s *ModelsService) Classes(ctx context.Context) (*ModelClasses, error) {
	var out ModelClasses
	err := s.client.requestJSON(ctx, http.MethodGet, "/v1/playground/model-classes", requestOptions{auth: "none"}, &out)
	return &out, err
}
