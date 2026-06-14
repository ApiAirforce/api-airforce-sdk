// Package airforce is the official Go SDK for the api.airforce AI gateway.
package airforce

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"math"
	"math/rand"
	"net/http"
	"net/url"
	"os"
	"strings"
	"time"
)

const (
	defaultBaseURL = "https://api.airforce"
	version        = "0.0.1"
)

// 409 is intentionally excluded: a terminal business conflict (e.g. "already
// subscribed" on checkout), not a transient error worth retrying.
var retryableStatus = map[int]bool{408: true, 429: true, 500: true, 502: true, 503: true, 504: true}

// Client is the api.airforce API client. Create one with New.
type Client struct {
	apiKey       string
	sessionToken string
	baseURL      string
	httpClient   *http.Client
	maxRetries   int
	headers      map[string]string

	Chat      *ChatService
	Messages  *MessagesService
	Responses *ResponsesService
	Gemini    *GeminiService
	Models    *ModelsService
	Images    *ImagesService
	Audio     *AudioService
	Video     *VideoService
	Voices    *VoicesService
	Account   *AccountService
	Keys      *KeysService
	Billing   *BillingService
	TwoFactor *TwoFactorService
	Auth      *AuthService
	OAuth     *OAuthService
}

// Option configures a Client.
type Option func(*Client)

// WithAPIKey sets the API key (sk-air-...).
func WithAPIKey(key string) Option { return func(c *Client) { c.apiKey = key } }

// WithSessionToken sets the session JWT used for account/billing endpoints.
func WithSessionToken(token string) Option { return func(c *Client) { c.sessionToken = token } }

// WithBaseURL overrides the API base URL.
func WithBaseURL(u string) Option { return func(c *Client) { c.baseURL = u } }

// WithHTTPClient injects a custom *http.Client.
func WithHTTPClient(h *http.Client) Option { return func(c *Client) { c.httpClient = h } }

// WithMaxRetries sets the number of automatic retries on 429/5xx/network errors.
func WithMaxRetries(n int) Option { return func(c *Client) { c.maxRetries = n } }

// WithTimeout sets the per-request timeout on the default HTTP client.
func WithTimeout(d time.Duration) Option {
	return func(c *Client) { c.httpClient.Timeout = d }
}

// WithHeader adds a header sent on every request.
func WithHeader(key, value string) Option {
	return func(c *Client) { c.headers[key] = value }
}

// New creates a Client. The API key falls back to AIRFORCE_API_KEY.
func New(opts ...Option) *Client {
	c := &Client{
		apiKey:       os.Getenv("AIRFORCE_API_KEY"),
		sessionToken: os.Getenv("AIRFORCE_SESSION_TOKEN"),
		baseURL:      defaultBaseURL,
		httpClient:   &http.Client{Timeout: 60 * time.Second},
		maxRetries:   2,
		headers:      map[string]string{},
	}
	if v := os.Getenv("AIRFORCE_BASE_URL"); v != "" {
		c.baseURL = v
	}
	for _, o := range opts {
		o(c)
	}
	c.baseURL = strings.TrimRight(c.baseURL, "/")

	c.Chat = &ChatService{c}
	c.Messages = &MessagesService{c}
	c.Responses = &ResponsesService{c}
	c.Gemini = &GeminiService{c}
	c.Models = &ModelsService{c}
	c.Images = &ImagesService{c}
	c.Audio = &AudioService{c}
	c.Video = &VideoService{c}
	c.Voices = &VoicesService{c}
	c.Account = &AccountService{c}
	c.Keys = &KeysService{c}
	c.Billing = &BillingService{c}
	c.TwoFactor = &TwoFactorService{c}
	c.Auth = &AuthService{c}
	c.OAuth = &OAuthService{c}
	return c
}

// SetSessionToken updates the session token (e.g. after Auth.Login).
func (c *Client) SetSessionToken(token string) { c.sessionToken = token }

// BaseURL returns the configured base URL.
func (c *Client) BaseURL() string { return c.baseURL }

type requestOptions struct {
	auth        string // "api_key" (default), "session", or "none"
	query       url.Values
	body        []byte
	contentType string
	headers     map[string]string
}

func (c *Client) resolveToken(auth string) (string, error) {
	switch auth {
	case "none":
		return "", nil
	case "session":
		// Session endpoints require a session JWT — never substitute an API key.
		if c.sessionToken != "" {
			return c.sessionToken, nil
		}
	default:
		if c.apiKey != "" {
			return c.apiKey, nil
		}
		if c.sessionToken != "" {
			return c.sessionToken, nil
		}
	}
	return "", ErrMissingCredential
}

func (c *Client) buildRequest(ctx context.Context, method, u string, o requestOptions, token string, stream bool) (*http.Request, error) {
	var body io.Reader
	if o.body != nil {
		body = bytes.NewReader(o.body)
	}
	req, err := http.NewRequestWithContext(ctx, method, u, body)
	if err != nil {
		return nil, err
	}
	req.Header.Set("user-agent", "airforce-sdk-go/"+version)
	req.Header.Set("x-airforce-sdk", "go/"+version)
	if stream {
		req.Header.Set("accept", "text/event-stream")
	} else {
		req.Header.Set("accept", "application/json")
	}
	if o.contentType != "" {
		req.Header.Set("content-type", o.contentType)
	}
	if token != "" {
		req.Header.Set("authorization", "Bearer "+token)
	}
	for k, v := range c.headers {
		req.Header.Set(k, v)
	}
	for k, v := range o.headers {
		req.Header.Set(k, v)
	}
	return req, nil
}

func (c *Client) do(ctx context.Context, method, path string, o requestOptions, stream bool) (*http.Response, error) {
	if o.auth == "" {
		o.auth = "api_key"
	}
	token, err := c.resolveToken(o.auth)
	if err != nil {
		return nil, err
	}
	u := c.baseURL + "/" + strings.TrimPrefix(path, "/")
	if len(o.query) > 0 {
		u += "?" + o.query.Encode()
	}

	for attempt := 0; ; attempt++ {
		req, err := c.buildRequest(ctx, method, u, o, token, stream)
		if err != nil {
			return nil, err
		}
		resp, err := c.httpClient.Do(req)
		if err != nil {
			// A transport error leaves a POST's outcome unknown — retrying could
			// double-charge a billable request. Only retry idempotent methods.
			if attempt < c.maxRetries && ctx.Err() == nil && method != http.MethodPost {
				if !sleepCtx(ctx, backoff(attempt+1, 0)) {
					return nil, ctx.Err()
				}
				continue
			}
			return nil, fmt.Errorf("airforce: request to %s failed: %w", path, err)
		}
		if resp.StatusCode < 400 {
			return resp, nil
		}
		if retryableStatus[resp.StatusCode] && attempt < c.maxRetries {
			ra := retryAfterSeconds(resp)
			resp.Body.Close()
			if !sleepCtx(ctx, backoff(attempt+1, ra)) {
				return nil, ctx.Err()
			}
			continue
		}
		body, _ := io.ReadAll(resp.Body)
		resp.Body.Close()
		return nil, parseAPIError(resp.StatusCode, body, resp.Header)
	}
}

// getJSON / postJSON etc. — typed convenience wrappers.

func (c *Client) requestJSON(ctx context.Context, method, path string, o requestOptions, out any) error {
	resp, err := c.do(ctx, method, path, o, false)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if out == nil || resp.StatusCode == http.StatusNoContent {
		io.Copy(io.Discard, resp.Body)
		return nil
	}
	return json.NewDecoder(resp.Body).Decode(out)
}

// requestJSONCookie decodes the response and returns the airforce_session
// cookie value (if any) — used by the auth login/signup flow.
func (c *Client) requestJSONCookie(ctx context.Context, method, path string, o requestOptions, out any) (string, error) {
	resp, err := c.do(ctx, method, path, o, false)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()
	if out != nil {
		if err := json.NewDecoder(resp.Body).Decode(out); err != nil {
			return "", err
		}
	} else {
		io.Copy(io.Discard, resp.Body)
	}
	for _, ck := range resp.Cookies() {
		if ck.Name == "airforce_session" {
			return ck.Value, nil
		}
	}
	return "", nil
}

func (c *Client) requestBytes(ctx context.Context, method, path string, o requestOptions) ([]byte, error) {
	resp, err := c.do(ctx, method, path, o, false)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	return io.ReadAll(resp.Body)
}

func (c *Client) postJSON(ctx context.Context, path, auth string, params, out any) error {
	return c.postJSONMethod(ctx, http.MethodPost, path, auth, params, out)
}

func (c *Client) postJSONMethod(ctx context.Context, method, path, auth string, params, out any) error {
	o, err := jsonOptions(auth, params)
	if err != nil {
		return err
	}
	return c.requestJSON(ctx, method, path, o, out)
}

func (c *Client) getJSON(ctx context.Context, path, auth string, query url.Values, out any) error {
	return c.requestJSON(ctx, http.MethodGet, path, requestOptions{auth: auth, query: query}, out)
}

func (c *Client) deleteJSON(ctx context.Context, path, auth string, out any) error {
	return c.requestJSON(ctx, http.MethodDelete, path, requestOptions{auth: auth}, out)
}

func jsonOptions(auth string, params any) (requestOptions, error) {
	o := requestOptions{auth: auth}
	if params != nil {
		b, err := json.Marshal(params)
		if err != nil {
			return o, err
		}
		o.body = b
		o.contentType = "application/json"
	}
	return o, nil
}

func doStream[T any](ctx context.Context, c *Client, path, auth string, params any) (*Stream[T], error) {
	o, err := jsonOptions(auth, params)
	if err != nil {
		return nil, err
	}
	resp, err := c.do(ctx, http.MethodPost, path, o, true)
	if err != nil {
		return nil, err
	}
	return newStream[T](resp), nil
}

func retryAfterSeconds(resp *http.Response) float64 {
	if v := resp.Header.Get("retry-after"); v != "" {
		var secs float64
		if _, err := fmt.Sscanf(v, "%f", &secs); err == nil {
			return secs
		}
	}
	return 0
}

func backoff(attempt int, retryAfter float64) time.Duration {
	base := retryAfter
	if base == 0 {
		base = math.Min(math.Pow(2, float64(attempt-1)), 8)
	}
	jitter := base * 0.25 * rand.Float64()
	return time.Duration((base + jitter) * float64(time.Second))
}

func sleepCtx(ctx context.Context, d time.Duration) bool {
	t := time.NewTimer(d)
	defer t.Stop()
	select {
	case <-ctx.Done():
		return false
	case <-t.C:
		return true
	}
}
