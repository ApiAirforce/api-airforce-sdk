package airforce

import (
	"context"
	"net/http"
	"net/url"
	"strconv"
)

// AccountService accesses /api/me and /api/user/*.
type AccountService struct{ client *Client }

// Me returns the current user profile + quotas.
func (s *AccountService) Me(ctx context.Context) (map[string]any, error) {
	var out map[string]any
	err := s.client.getJSON(ctx, "/api/me", "session", nil, &out)
	return out, err
}

// Usage returns the account + billing summary.
func (s *AccountService) Usage(ctx context.Context) (map[string]any, error) {
	var out map[string]any
	err := s.client.getJSON(ctx, "/api/usage", "session", nil, &out)
	return out, err
}

// MyUsage returns the detailed usage log + aggregates.
func (s *AccountService) MyUsage(ctx context.Context) (map[string]any, error) {
	var out map[string]any
	err := s.client.getJSON(ctx, "/api/my-usage", "session", nil, &out)
	return out, err
}

// Update changes username / email / password.
func (s *AccountService) Update(ctx context.Context, params map[string]any) (map[string]any, error) {
	var out map[string]any
	err := s.client.postJSONMethod(ctx, http.MethodPut, "/api/user/update", "session", params, &out)
	return out, err
}

// RequestPasswordReset sends a reset email.
func (s *AccountService) RequestPasswordReset(ctx context.Context, email, locale string) (map[string]any, error) {
	body := map[string]any{"email": email}
	if locale != "" {
		body["locale"] = locale
	}
	var out map[string]any
	err := s.client.postJSON(ctx, "/api/auth/request-password-reset", "none", body, &out)
	return out, err
}

// ResetPassword completes a password reset.
func (s *AccountService) ResetPassword(ctx context.Context, token, newPassword string) (map[string]any, error) {
	var out map[string]any
	err := s.client.postJSON(ctx, "/api/auth/reset-password", "none", map[string]any{"token": token, "new_password": newPassword}, &out)
	return out, err
}

// ReferralCode returns the caller's referral code.
func (s *AccountService) ReferralCode(ctx context.Context) (map[string]any, error) {
	var out map[string]any
	err := s.client.getJSON(ctx, "/api/referral/code", "session", nil, &out)
	return out, err
}

// ReferredUsers lists users referred by the caller.
func (s *AccountService) ReferredUsers(ctx context.Context) (map[string]any, error) {
	var out map[string]any
	err := s.client.getJSON(ctx, "/api/referral/referred-users", "session", nil, &out)
	return out, err
}

// GetPriceCaps returns per-model price ceilings.
func (s *AccountService) GetPriceCaps(ctx context.Context) (map[string]any, error) {
	var out map[string]any
	err := s.client.getJSON(ctx, "/api/user/price-caps", "session", nil, &out)
	return out, err
}

// SetPriceCaps replaces all per-model price caps.
func (s *AccountService) SetPriceCaps(ctx context.Context, caps map[string]any) (map[string]any, error) {
	var out map[string]any
	err := s.client.postJSONMethod(ctx, http.MethodPut, "/api/user/price-caps", "session", map[string]any{"caps": caps}, &out)
	return out, err
}

// DeletePriceCap removes one model's price cap.
func (s *AccountService) DeletePriceCap(ctx context.Context, model string) error {
	return s.client.deleteJSON(ctx, "/api/user/price-caps/"+url.PathEscape(model), "session", nil)
}

// GetModelAliases returns all model aliases.
func (s *AccountService) GetModelAliases(ctx context.Context) (map[string]any, error) {
	var out map[string]any
	err := s.client.getJSON(ctx, "/api/user/model-aliases", "session", nil, &out)
	return out, err
}

// SetModelAlias adds or updates one alias.
func (s *AccountService) SetModelAlias(ctx context.Context, alias, model string) (map[string]any, error) {
	var out map[string]any
	err := s.client.postJSONMethod(ctx, http.MethodPut, "/api/user/model-aliases", "session", map[string]any{"alias": alias, "model": model}, &out)
	return out, err
}

// SetModelAliasesBatch upserts multiple aliases.
func (s *AccountService) SetModelAliasesBatch(ctx context.Context, aliases []map[string]string) (map[string]any, error) {
	var out map[string]any
	err := s.client.postJSONMethod(ctx, http.MethodPut, "/api/user/model-aliases/batch", "session", aliases, &out)
	return out, err
}

// DeleteModelAlias removes one alias.
func (s *AccountService) DeleteModelAlias(ctx context.Context, alias string) error {
	return s.client.deleteJSON(ctx, "/api/user/model-aliases/"+url.PathEscape(alias), "session", nil)
}

// GetModelDefaults returns all per-model parameter defaults.
func (s *AccountService) GetModelDefaults(ctx context.Context) (map[string]any, error) {
	var out map[string]any
	err := s.client.getJSON(ctx, "/api/user/model-defaults", "session", nil, &out)
	return out, err
}

// SetModelDefault sets per-model parameter defaults.
func (s *AccountService) SetModelDefault(ctx context.Context, model string, def map[string]any) (map[string]any, error) {
	var out map[string]any
	err := s.client.postJSONMethod(ctx, http.MethodPut, "/api/user/model-defaults/"+url.PathEscape(model), "session", def, &out)
	return out, err
}

// DeleteModelDefault clears a model's defaults.
func (s *AccountService) DeleteModelDefault(ctx context.Context, model string) error {
	return s.client.deleteJSON(ctx, "/api/user/model-defaults/"+url.PathEscape(model), "session", nil)
}

// GetSmartRouting returns the user's smart-routing config.
func (s *AccountService) GetSmartRouting(ctx context.Context) (map[string]any, error) {
	var out map[string]any
	err := s.client.getJSON(ctx, "/api/user/smart-routing", "api_key", nil, &out)
	return out, err
}

// SetSmartRouting sets the user's smart-routing groups.
func (s *AccountService) SetSmartRouting(ctx context.Context, groups map[string]any) (map[string]any, error) {
	var out map[string]any
	err := s.client.postJSONMethod(ctx, http.MethodPut, "/api/user/smart-routing", "api_key", map[string]any{"groups": groups}, &out)
	return out, err
}

// TestSmartRouting resolves a model through smart routing.
func (s *AccountService) TestSmartRouting(ctx context.Context, model string) (map[string]any, error) {
	var out map[string]any
	err := s.client.getJSON(ctx, "/api/user/smart-routing/test", "api_key", url.Values{"model": {model}}, &out)
	return out, err
}

// GetChannelPrefs returns per-model channel preferences.
func (s *AccountService) GetChannelPrefs(ctx context.Context) (map[string]any, error) {
	var out map[string]any
	err := s.client.getJSON(ctx, "/api/user/channel-prefs", "api_key", nil, &out)
	return out, err
}

// SetChannelPins sets per-model channel pins.
func (s *AccountService) SetChannelPins(ctx context.Context, pins map[string]string) (map[string]any, error) {
	var out map[string]any
	err := s.client.postJSONMethod(ctx, http.MethodPut, "/api/user/channel-prefs", "api_key", pins, &out)
	return out, err
}

// Sessions lists active sessions.
func (s *AccountService) Sessions(ctx context.Context) (map[string]any, error) {
	var out map[string]any
	err := s.client.getJSON(ctx, "/api/me/sessions", "session", nil, &out)
	return out, err
}

// RevokeSession revokes one session by jti.
func (s *AccountService) RevokeSession(ctx context.Context, jti string) error {
	return s.client.deleteJSON(ctx, "/api/me/sessions/"+url.PathEscape(jti), "session", nil)
}

// RevokeOtherSessions revokes all sessions except the current one.
func (s *AccountService) RevokeOtherSessions(ctx context.Context) (map[string]any, error) {
	var out map[string]any
	err := s.client.deleteJSON(ctx, "/api/me/sessions", "session", &out)
	return out, err
}

// LoginHistory returns the caller's login audit trail.
func (s *AccountService) LoginHistory(ctx context.Context, limit int) (map[string]any, error) {
	var query url.Values
	if limit > 0 {
		query = url.Values{"limit": {strconv.Itoa(limit)}}
	}
	var out map[string]any
	err := s.client.getJSON(ctx, "/api/me/login-history", "session", query, &out)
	return out, err
}

// ResetAPIKey rotates the primary API key.
func (s *AccountService) ResetAPIKey(ctx context.Context) (map[string]any, error) {
	var out map[string]any
	err := s.client.postJSON(ctx, "/api/user/reset-api-key", "session", nil, &out)
	return out, err
}

// SetPrimaryAllowedIPs sets the IP whitelist for the primary key.
func (s *AccountService) SetPrimaryAllowedIPs(ctx context.Context, ips []string) (map[string]any, error) {
	var out map[string]any
	err := s.client.postJSONMethod(ctx, http.MethodPut, "/api/user/primary-allowed-ips", "session", map[string]any{"allowed_ips": ips}, &out)
	return out, err
}

// SetBackupPoolEnabled toggles the backup pool.
func (s *AccountService) SetBackupPoolEnabled(ctx context.Context, enabled bool) (map[string]any, error) {
	var out map[string]any
	err := s.client.postJSONMethod(ctx, http.MethodPut, "/api/user/backup-pool-enabled", "api_key", map[string]any{"enabled": enabled}, &out)
	return out, err
}

// TogglePayAsYouGo flips pay-as-you-go spending.
func (s *AccountService) TogglePayAsYouGo(ctx context.Context) (map[string]any, error) {
	var out map[string]any
	err := s.client.postJSON(ctx, "/api/pay-as-you-go/toggle", "session", nil, &out)
	return out, err
}

// --- keys --------------------------------------------------------------------

// APIKey is a provisioned API key.
type APIKey struct {
	Key             string   `json:"key"`
	Label           string   `json:"label,omitempty"`
	Disabled        bool     `json:"disabled,omitempty"`
	Tier            string   `json:"tier"`
	RPMLimit        *int     `json:"rpm_limit,omitempty"`
	CreditAllowance *float64 `json:"credit_allowance,omitempty"`
	LimitReset      string   `json:"limit_reset,omitempty"`
	AllowedModels   []string `json:"allowed_models"`
	AllowedIPs      []string `json:"allowed_ips"`
}

// KeysService accesses /v1/keys.
type KeysService struct{ client *Client }

// Create makes a secondary key. The full key is returned only here.
func (s *KeysService) Create(ctx context.Context, params map[string]any) (*APIKey, error) {
	var out APIKey
	err := s.client.postJSON(ctx, "/v1/keys", "api_key", params, &out)
	return &out, err
}

// List returns the secondary keys (masked).
func (s *KeysService) List(ctx context.Context) ([]APIKey, error) {
	var out struct {
		Keys []APIKey `json:"keys"`
	}
	err := s.client.getJSON(ctx, "/v1/keys", "api_key", nil, &out)
	return out.Keys, err
}

// Update changes a secondary key's settings.
func (s *KeysService) Update(ctx context.Context, key string, params map[string]any) (*APIKey, error) {
	var out APIKey
	err := s.client.postJSONMethod(ctx, http.MethodPatch, "/v1/keys/"+url.PathEscape(key), "api_key", params, &out)
	return &out, err
}

// Delete removes a secondary key.
func (s *KeysService) Delete(ctx context.Context, key string) error {
	return s.client.deleteJSON(ctx, "/v1/keys/"+url.PathEscape(key), "api_key", nil)
}

// --- billing -----------------------------------------------------------------

// BillingService accesses billing/plans/analytics.
type BillingService struct{ client *Client }

// CreateCheckout creates a Creem checkout session.
func (s *BillingService) CreateCheckout(ctx context.Context, params map[string]any) (map[string]any, error) {
	var out map[string]any
	err := s.client.postJSON(ctx, "/api/creem/create-checkout", "session", params, &out)
	return out, err
}

// CreateCryptoInvoice creates a NowPayments crypto invoice.
func (s *BillingService) CreateCryptoInvoice(ctx context.Context, params map[string]any) (map[string]any, error) {
	var out map[string]any
	err := s.client.postJSON(ctx, "/api/create-nowpayments-invoice", "session", params, &out)
	return out, err
}

// CreatePortalSession creates a Creem customer-portal session.
func (s *BillingService) CreatePortalSession(ctx context.Context) (map[string]any, error) {
	var out map[string]any
	err := s.client.postJSON(ctx, "/api/create-portal-session", "session", map[string]any{}, &out)
	return out, err
}

// Analytics returns the public global analytics snapshot.
func (s *BillingService) Analytics(ctx context.Context) (map[string]any, error) {
	var out map[string]any
	err := s.client.getJSON(ctx, "/v1/analytics", "none", nil, &out)
	return out, err
}
