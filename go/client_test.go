package airforce

import (
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"testing"
)

const completionJSON = `{"id":"cmpl_1","object":"chat.completion","created":0,"model":"claude-opus-4.8",` +
	`"choices":[{"index":0,"message":{"role":"assistant","content":"hi"},"finish_reason":"stop"}]}`

func newTestClient(t *testing.T, handler http.HandlerFunc, opts ...Option) *Client {
	t.Helper()
	srv := httptest.NewServer(handler)
	t.Cleanup(srv.Close)
	return New(append([]Option{WithBaseURL(srv.URL)}, opts...)...)
}

func TestChatCreate(t *testing.T) {
	var gotAuth, gotPath string
	client := newTestClient(t, func(w http.ResponseWriter, r *http.Request) {
		gotAuth = r.Header.Get("authorization")
		gotPath = r.URL.Path
		w.Header().Set("content-type", "application/json")
		w.Write([]byte(completionJSON))
	}, WithAPIKey("sk-air-test"))

	res, err := client.Chat.Create(context.Background(), ChatCompletionParams{
		Model:    "claude-opus-4.8",
		Messages: []ChatMessage{{Role: "user", Content: "hello"}},
	})
	if err != nil {
		t.Fatal(err)
	}
	if res.Choices[0].Message.Content != "hi" {
		t.Fatalf("content = %q", res.Choices[0].Message.Content)
	}
	if gotAuth != "Bearer sk-air-test" {
		t.Fatalf("auth = %q", gotAuth)
	}
	if gotPath != "/v1/chat/completions" {
		t.Fatalf("path = %q", gotPath)
	}
}

func TestMissingCredential(t *testing.T) {
	client := newTestClient(t, func(w http.ResponseWriter, r *http.Request) {})
	_, err := client.Chat.Create(context.Background(), ChatCompletionParams{Model: "m", Messages: []ChatMessage{{Role: "user", Content: "x"}}})
	if !errors.Is(err, ErrMissingCredential) {
		t.Fatalf("expected ErrMissingCredential, got %v", err)
	}
}

func TestSessionEndpointRequiresSessionToken(t *testing.T) {
	// Account.Me is a session endpoint; an API key must NOT be substituted.
	client := newTestClient(t, func(w http.ResponseWriter, r *http.Request) {
		w.Write([]byte("{}"))
	}, WithAPIKey("sk-air-test"))
	_, err := client.Account.Me(context.Background())
	if !errors.Is(err, ErrMissingCredential) {
		t.Fatalf("expected ErrMissingCredential, got %v", err)
	}
}

func TestPublicEndpointHasNoAuth(t *testing.T) {
	var hadAuth bool
	client := newTestClient(t, func(w http.ResponseWriter, r *http.Request) {
		hadAuth = r.Header.Get("authorization") != ""
		w.Write([]byte(`{"object":"list","data":[]}`))
	})
	if _, err := client.Models.List(context.Background(), false); err != nil {
		t.Fatal(err)
	}
	if hadAuth {
		t.Fatal("public endpoint should not send authorization")
	}
}

func TestRetryOn429(t *testing.T) {
	n := 0
	client := newTestClient(t, func(w http.ResponseWriter, r *http.Request) {
		n++
		if n == 1 {
			w.Header().Set("retry-after", "0")
			w.WriteHeader(http.StatusTooManyRequests)
			w.Write([]byte(`{"error":"slow"}`))
			return
		}
		w.Write([]byte(completionJSON))
	}, WithAPIKey("sk-air-test"))

	res, err := client.Chat.Create(context.Background(), ChatCompletionParams{Model: "m", Messages: []ChatMessage{{Role: "user", Content: "x"}}})
	if err != nil {
		t.Fatal(err)
	}
	if res.ID != "cmpl_1" || n != 2 {
		t.Fatalf("id=%q calls=%d", res.ID, n)
	}
}

func TestErrorMapping(t *testing.T) {
	client := newTestClient(t, func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusPaymentRequired)
		w.Write([]byte(`{"error":{"message":"no balance","code":"insufficient_balance"}}`))
	}, WithAPIKey("sk-air-test"))

	_, err := client.Chat.Create(context.Background(), ChatCompletionParams{Model: "m", Messages: []ChatMessage{{Role: "user", Content: "x"}}})
	var apiErr *APIError
	if !errors.As(err, &apiErr) {
		t.Fatalf("expected *APIError, got %v", err)
	}
	if apiErr.Status != 402 || !apiErr.IsInsufficientBalance() || apiErr.Code != "insufficient_balance" {
		t.Fatalf("got %+v", apiErr)
	}
}

func TestStreaming(t *testing.T) {
	client := newTestClient(t, func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("content-type", "text/event-stream")
		fl, _ := w.(http.Flusher)
		for _, chunk := range []string{
			`data: {"choices":[{"index":0,"delta":{"content":"he"},"finish_reason":null}]}` + "\n\n",
			`data: {"choices":[{"index":0,"delta":{"content":"llo"},"finish_reason":"stop"}]}` + "\n\n",
			"data: [DONE]\n\n",
		} {
			w.Write([]byte(chunk))
			if fl != nil {
				fl.Flush()
			}
		}
	}, WithAPIKey("sk-air-test"))

	stream, err := client.Chat.CreateStream(context.Background(), ChatCompletionParams{Model: "m", Messages: []ChatMessage{{Role: "user", Content: "x"}}})
	if err != nil {
		t.Fatal(err)
	}
	defer stream.Close()
	text := ""
	for stream.Next() {
		for _, c := range stream.Current().Choices {
			text += c.Delta.Content
		}
	}
	if err := stream.Err(); err != nil {
		t.Fatal(err)
	}
	if text != "hello" {
		t.Fatalf("text = %q", text)
	}
}

func TestParseErrorFlat(t *testing.T) {
	apiErr := parseAPIError(400, []byte(`{"error":"bad thing"}`), http.Header{})
	if apiErr.Message != "bad thing" {
		t.Fatalf("message = %q", apiErr.Message)
	}
	// sanity: ensure JSON helper compiles against encoding/json
	_ = json.Marshal
}
