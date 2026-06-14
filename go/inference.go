package airforce

import (
	"context"
	"net/url"
)

// --- shared types ------------------------------------------------------------

// ChatMessage is one message in a chat conversation. Content is a string or a
// slice of content parts (for vision).
type ChatMessage struct {
	Role       string     `json:"role"`
	Content    any        `json:"content"`
	Name       string     `json:"name,omitempty"`
	ToolCallID string     `json:"tool_call_id,omitempty"`
	ToolCalls  []ToolCall `json:"tool_calls,omitempty"`
}

// Tool describes a callable function tool.
type Tool struct {
	Type     string             `json:"type"`
	Function FunctionDefinition `json:"function"`
}

// FunctionDefinition is the schema of a function tool.
type FunctionDefinition struct {
	Name        string         `json:"name"`
	Description string         `json:"description,omitempty"`
	Parameters  map[string]any `json:"parameters,omitempty"`
}

// ToolCall is a tool invocation emitted by the model.
type ToolCall struct {
	Index    int    `json:"index,omitempty"`
	ID       string `json:"id"`
	Type     string `json:"type"`
	Function struct {
		Name      string `json:"name"`
		Arguments string `json:"arguments"`
	} `json:"function"`
}

// Usage holds token accounting for a completion.
type Usage struct {
	PromptTokens        int `json:"prompt_tokens"`
	CompletionTokens    int `json:"completion_tokens"`
	TotalTokens         int `json:"total_tokens"`
	PromptTokensDetails *struct {
		CachedTokens int `json:"cached_tokens"`
	} `json:"prompt_tokens_details,omitempty"`
	CacheCreationInputTokens int `json:"cache_creation_input_tokens,omitempty"`
	// Cost is the request cost in credits (USD).
	Cost *float64 `json:"cost,omitempty"`
}

// --- chat --------------------------------------------------------------------

// ChatCompletionParams is the request for Chat.Create.
type ChatCompletionParams struct {
	Model           string        `json:"model"`
	Messages        []ChatMessage `json:"messages"`
	MaxTokens       int           `json:"max_tokens,omitempty"`
	Temperature     *float64      `json:"temperature,omitempty"`
	TopP            *float64      `json:"top_p,omitempty"`
	Stop            []string      `json:"stop,omitempty"`
	Tools           []Tool        `json:"tools,omitempty"`
	ToolChoice      any           `json:"tool_choice,omitempty"`
	ResponseFormat  any           `json:"response_format,omitempty"`
	ReasoningEffort string        `json:"reasoning_effort,omitempty"`
	Thinking        any           `json:"thinking,omitempty"`
	ThinkingBudget  int           `json:"thinking_budget,omitempty"`
	// Models is the airforce fallback array (up to 3).
	Models     []string `json:"models,omitempty"`
	Skill      string   `json:"skill,omitempty"`
	Skills     []string `json:"skills,omitempty"`
	Transforms []string `json:"transforms,omitempty"`
	Stream     bool     `json:"stream,omitempty"`
}

// ChatCompletion is a non-streaming chat response.
type ChatCompletion struct {
	ID      string `json:"id"`
	Object  string `json:"object"`
	Created int64  `json:"created"`
	Model   string `json:"model"`
	Choices []struct {
		Index   int `json:"index"`
		Message struct {
			Role      string     `json:"role"`
			Content   string     `json:"content"`
			Reasoning string     `json:"reasoning,omitempty"`
			ToolCalls []ToolCall `json:"tool_calls,omitempty"`
		} `json:"message"`
		FinishReason string `json:"finish_reason"`
	} `json:"choices"`
	Usage *Usage `json:"usage,omitempty"`
}

// ChatCompletionChunk is one streaming chat delta.
type ChatCompletionChunk struct {
	ID      string `json:"id"`
	Object  string `json:"object"`
	Created int64  `json:"created"`
	Model   string `json:"model"`
	Choices []struct {
		Index int `json:"index"`
		Delta struct {
			Role      string     `json:"role,omitempty"`
			Content   string     `json:"content,omitempty"`
			Reasoning string     `json:"reasoning,omitempty"`
			ToolCalls []ToolCall `json:"tool_calls,omitempty"`
		} `json:"delta"`
		FinishReason *string `json:"finish_reason"`
	} `json:"choices"`
	Usage *Usage `json:"usage,omitempty"`
}

// ChatService accesses /v1/chat/completions.
type ChatService struct{ client *Client }

// Create performs a non-streaming chat completion.
func (s *ChatService) Create(ctx context.Context, params ChatCompletionParams) (*ChatCompletion, error) {
	params.Stream = false
	var out ChatCompletion
	if err := s.client.postJSON(ctx, "/v1/chat/completions", "api_key", params, &out); err != nil {
		return nil, err
	}
	return &out, nil
}

// CreateStream performs a streaming chat completion.
func (s *ChatService) CreateStream(ctx context.Context, params ChatCompletionParams) (*Stream[ChatCompletionChunk], error) {
	params.Stream = true
	return doStream[ChatCompletionChunk](ctx, s.client, "/v1/chat/completions", "api_key", params)
}

// --- messages (Anthropic) ----------------------------------------------------

// MessageParams is the request for Messages.Create.
type MessageParams struct {
	Model         string           `json:"model"`
	Messages      []map[string]any `json:"messages"`
	MaxTokens     int              `json:"max_tokens"`
	System        any              `json:"system,omitempty"`
	Temperature   *float64         `json:"temperature,omitempty"`
	TopP          *float64         `json:"top_p,omitempty"`
	TopK          int              `json:"top_k,omitempty"`
	StopSequences []string         `json:"stop_sequences,omitempty"`
	Tools         []map[string]any `json:"tools,omitempty"`
	ToolChoice    any              `json:"tool_choice,omitempty"`
	Thinking      any              `json:"thinking,omitempty"`
	Fallbacks     []map[string]any `json:"fallbacks,omitempty"`
	Models        []string         `json:"models,omitempty"`
	Stream        bool             `json:"stream,omitempty"`
}

// Message is a non-streaming Anthropic response.
type Message struct {
	ID           string           `json:"id"`
	Type         string           `json:"type"`
	Role         string           `json:"role"`
	Content      []map[string]any `json:"content"`
	Model        string           `json:"model"`
	StopReason   string           `json:"stop_reason"`
	StopSequence *string          `json:"stop_sequence"`
	Usage        map[string]any   `json:"usage"`
}

// MessageStreamEvent is one streaming Messages event.
type MessageStreamEvent map[string]any

// MessagesService accesses /v1/messages.
type MessagesService struct{ client *Client }

// Create performs a non-streaming message.
func (s *MessagesService) Create(ctx context.Context, params MessageParams) (*Message, error) {
	params.Stream = false
	var out Message
	if err := s.client.postJSON(ctx, "/v1/messages", "api_key", params, &out); err != nil {
		return nil, err
	}
	return &out, nil
}

// CreateStream performs a streaming message.
func (s *MessagesService) CreateStream(ctx context.Context, params MessageParams) (*Stream[MessageStreamEvent], error) {
	params.Stream = true
	return doStream[MessageStreamEvent](ctx, s.client, "/v1/messages", "api_key", params)
}

// CountTokens estimates the token count of a prompt locally.
func (s *MessagesService) CountTokens(ctx context.Context, params map[string]any) (map[string]any, error) {
	var out map[string]any
	err := s.client.postJSON(ctx, "/v1/messages/count_tokens", "api_key", params, &out)
	return out, err
}

// --- responses ---------------------------------------------------------------

// ResponseParams is the request for Responses.Create.
type ResponseParams struct {
	Model           string   `json:"model"`
	Input           any      `json:"input"`
	Instructions    string   `json:"instructions,omitempty"`
	Tools           []Tool   `json:"tools,omitempty"`
	ToolChoice      any      `json:"tool_choice,omitempty"`
	MaxOutputTokens int      `json:"max_output_tokens,omitempty"`
	Temperature     *float64 `json:"temperature,omitempty"`
	TopP            *float64 `json:"top_p,omitempty"`
	Reasoning       any      `json:"reasoning,omitempty"`
	Stream          bool     `json:"stream,omitempty"`
}

// ResponseStreamEvent is one streaming Responses event.
type ResponseStreamEvent map[string]any

// ResponsesService accesses /v1/responses.
type ResponsesService struct{ client *Client }

// Create performs a non-streaming response.
func (s *ResponsesService) Create(ctx context.Context, params ResponseParams) (map[string]any, error) {
	params.Stream = false
	var out map[string]any
	err := s.client.postJSON(ctx, "/v1/responses", "api_key", params, &out)
	return out, err
}

// CreateStream performs a streaming response.
func (s *ResponsesService) CreateStream(ctx context.Context, params ResponseParams) (*Stream[ResponseStreamEvent], error) {
	params.Stream = true
	return doStream[ResponseStreamEvent](ctx, s.client, "/v1/responses", "api_key", params)
}

// --- gemini (/v1beta) --------------------------------------------------------

// GeminiService accesses the Gemini-compatible generation surface.
type GeminiService struct{ client *Client }

func geminiPath(model, method string) string {
	return "/v1beta/models/" + url.PathEscape(model) + ":" + method
}

// GenerateContent performs a non-streaming Gemini generateContent.
func (s *GeminiService) GenerateContent(ctx context.Context, model string, params map[string]any) (map[string]any, error) {
	var out map[string]any
	err := s.client.postJSON(ctx, geminiPath(model, "generateContent"), "api_key", params, &out)
	return out, err
}

// StreamGenerateContent performs a streaming Gemini streamGenerateContent.
func (s *GeminiService) StreamGenerateContent(ctx context.Context, model string, params map[string]any) (*Stream[map[string]any], error) {
	return doStream[map[string]any](ctx, s.client, geminiPath(model, "streamGenerateContent"), "api_key", params)
}
