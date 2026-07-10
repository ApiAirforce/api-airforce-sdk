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

func TestEmbeddingsCreate(t *testing.T) {
	var gotAuth, gotPath string
	var gotBody map[string]any
	client := newTestClient(t, func(w http.ResponseWriter, r *http.Request) {
		gotAuth = r.Header.Get("authorization")
		gotPath = r.URL.Path
		json.NewDecoder(r.Body).Decode(&gotBody)
		w.Header().Set("content-type", "application/json")
		w.Write([]byte(`{"object":"list","data":[{"object":"embedding","index":0,"embedding":[0.1,0.2]}],` +
			`"model":"text-embedding-3-small","usage":{"prompt_tokens":2,"total_tokens":2}}`))
	}, WithAPIKey("sk-air-test"))

	res, err := client.Embeddings.Create(context.Background(), EmbeddingsParams{
		Model: "text-embedding-3-small",
		Input: "hello world",
	})
	if err != nil {
		t.Fatal(err)
	}
	if gotPath != "/v1/embeddings" || gotAuth != "Bearer sk-air-test" {
		t.Fatalf("path=%q auth=%q", gotPath, gotAuth)
	}
	if gotBody["input"] != "hello world" {
		t.Fatalf("input = %v", gotBody["input"])
	}
	if len(res.Data) != 1 || res.Data[0].Object != "embedding" {
		t.Fatalf("data = %+v", res.Data)
	}
	if res.Usage == nil || res.Usage.PromptTokens != 2 || res.Usage.TotalTokens != 2 {
		t.Fatalf("usage = %+v", res.Usage)
	}
}

func TestOrgMembers(t *testing.T) {
	var gotAuth, gotPath string
	client := newTestClient(t, func(w http.ResponseWriter, r *http.Request) {
		gotAuth = r.Header.Get("authorization")
		gotPath = r.URL.Path
		w.Write([]byte(`{"members":[{"user_id":7,"username":"pilot","role":"owner","status":"active"}]}`))
	}, WithSessionToken("jwt-test"))

	members, err := client.Org.Members(context.Background())
	if err != nil {
		t.Fatal(err)
	}
	if gotPath != "/api/org/members" || gotAuth != "Bearer jwt-test" {
		t.Fatalf("path=%q auth=%q", gotPath, gotAuth)
	}
	if len(members) != 1 || members[0]["role"] != "owner" {
		t.Fatalf("members = %+v", members)
	}
}

func TestNotificationsList(t *testing.T) {
	var gotPath, gotLimit, gotBefore string
	client := newTestClient(t, func(w http.ResponseWriter, r *http.Request) {
		gotPath = r.URL.Path
		gotLimit = r.URL.Query().Get("limit")
		gotBefore = r.URL.Query().Get("before")
		w.Write([]byte(`{"items":[{"id":"n_1","kind":"price_drop","created_at":"2026-07-01T00:00:00Z"}],"unread":3}`))
	}, WithSessionToken("jwt-test"))

	res, err := client.Notifications.List(context.Background(), 10, "2026-07-02T00:00:00Z")
	if err != nil {
		t.Fatal(err)
	}
	if gotPath != "/api/me/notifications" || gotLimit != "10" || gotBefore != "2026-07-02T00:00:00Z" {
		t.Fatalf("path=%q limit=%q before=%q", gotPath, gotLimit, gotBefore)
	}
	items, ok := res["items"].([]any)
	if !ok || len(items) != 1 || res["unread"] != float64(3) {
		t.Fatalf("res = %+v", res)
	}
}

func TestAccountClose(t *testing.T) {
	var gotMethod, gotPath string
	var gotBody map[string]any
	client := newTestClient(t, func(w http.ResponseWriter, r *http.Request) {
		gotMethod = r.Method
		gotPath = r.URL.Path
		json.NewDecoder(r.Body).Decode(&gotBody)
		w.Write([]byte(`{"closed":true}`))
	}, WithSessionToken("jwt-test"))

	res, err := client.Account.CloseAccount(context.Background(), "hunter2", "123456", true)
	if err != nil {
		t.Fatal(err)
	}
	if gotMethod != http.MethodDelete || gotPath != "/api/me/account" {
		t.Fatalf("method=%q path=%q", gotMethod, gotPath)
	}
	if gotBody["password"] != "hunter2" || gotBody["totp_code"] != "123456" || gotBody["forfeit_balance_ack"] != true {
		t.Fatalf("body = %+v", gotBody)
	}
	if res["closed"] != true {
		t.Fatalf("res = %+v", res)
	}
}

func TestThreeDContent(t *testing.T) {
	var gotPath string
	client := newTestClient(t, func(w http.ResponseWriter, r *http.Request) {
		gotPath = r.URL.Path
		w.Header().Set("content-type", "model/gltf-binary")
		w.Write([]byte("glTF-bytes"))
	}, WithAPIKey("sk-air-test"))

	data, err := client.ThreeD.Content(context.Background(), "task_1")
	if err != nil {
		t.Fatal(err)
	}
	if gotPath != "/v1/3d/tasks/task_1/content" {
		t.Fatalf("path = %q", gotPath)
	}
	if string(data) != "glTF-bytes" {
		t.Fatalf("data = %q", data)
	}
}
