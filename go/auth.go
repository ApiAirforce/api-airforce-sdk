package airforce

import (
	"context"
	"crypto/rand"
	"crypto/sha256"
	"encoding/base64"
	"net/http"
	"net/url"
	"strings"
)

// --- two-factor --------------------------------------------------------------

// TwoFactorService accesses /api/2fa/*.
type TwoFactorService struct{ client *Client }

func (s *TwoFactorService) post(ctx context.Context, path string, body map[string]any) (map[string]any, error) {
	var out map[string]any
	err := s.client.postJSON(ctx, path, "session", body, &out)
	return out, err
}

// SetupInit begins enrollment (returns secret + otpauth URL).
func (s *TwoFactorService) SetupInit(ctx context.Context) (map[string]any, error) {
	return s.post(ctx, "/api/2fa/setup-init", nil)
}

// SetupVerify verifies the first code and returns backup codes.
func (s *TwoFactorService) SetupVerify(ctx context.Context, code string) (map[string]any, error) {
	return s.post(ctx, "/api/2fa/setup-verify", map[string]any{"code": code})
}

// Disable turns off 2FA.
func (s *TwoFactorService) Disable(ctx context.Context, password, code string) (map[string]any, error) {
	return s.post(ctx, "/api/2fa/disable", map[string]any{"password": password, "code": code})
}

// RegenerateBackupCodes issues new backup codes.
func (s *TwoFactorService) RegenerateBackupCodes(ctx context.Context, code string) (map[string]any, error) {
	return s.post(ctx, "/api/2fa/regenerate-backup-codes", map[string]any{"code": code})
}

// VerifyStepUp performs step-up verification.
func (s *TwoFactorService) VerifyStepUp(ctx context.Context, code string) (map[string]any, error) {
	return s.post(ctx, "/api/2fa/verify-step-up", map[string]any{"code": code})
}

// StepUpStatus checks current step-up status.
func (s *TwoFactorService) StepUpStatus(ctx context.Context) (map[string]any, error) {
	var out map[string]any
	err := s.client.getJSON(ctx, "/api/2fa/step-up-status", "session", nil, &out)
	return out, err
}

// --- auth --------------------------------------------------------------------

// AuthService accesses /auth/*. On successful login/signup the session token is
// adopted automatically.
type AuthService struct{ client *Client }

func (s *AuthService) submit(ctx context.Context, path string, body map[string]any, headers map[string]string) (map[string]any, error) {
	o, err := jsonOptions("none", body)
	if err != nil {
		return nil, err
	}
	o.headers = headers
	var out map[string]any
	token, err := s.client.requestJSONCookie(ctx, http.MethodPost, path, o, &out)
	if err != nil {
		return nil, err
	}
	if token != "" {
		s.client.sessionToken = token
		if out == nil {
			out = map[string]any{}
		}
		out["session_token"] = token
	}
	return out, nil
}

// Signup registers a new account.
func (s *AuthService) Signup(ctx context.Context, params map[string]any) (map[string]any, error) {
	return s.submit(ctx, "/auth/signup", params, nil)
}

// Login authenticates and adopts the session. May return a 2FA challenge.
func (s *AuthService) Login(ctx context.Context, username, password, captchaToken string) (map[string]any, error) {
	return s.submit(ctx, "/auth/login", map[string]any{
		"username": username, "password": password, "captcha_token": captchaToken,
	}, nil)
}

// Verify2FA completes a 2FA login with the challenge token.
func (s *AuthService) Verify2FA(ctx context.Context, challengeToken, code, backupCode string) (map[string]any, error) {
	body := map[string]any{"code": code}
	if backupCode != "" {
		body["backup_code"] = backupCode
	}
	return s.submit(ctx, "/auth/2fa/verify", body, map[string]string{"authorization": "Bearer " + challengeToken})
}

// VerifyEmail confirms an email-verification token.
func (s *AuthService) VerifyEmail(ctx context.Context, token string) (map[string]any, error) {
	var out map[string]any
	err := s.client.postJSON(ctx, "/auth/verify", "none", map[string]any{"token": token}, &out)
	return out, err
}

// ResendVerification resends the verification email.
func (s *AuthService) ResendVerification(ctx context.Context, identifier string) (map[string]any, error) {
	var out map[string]any
	err := s.client.postJSON(ctx, "/auth/resend-verification", "none", map[string]any{"identifier": identifier}, &out)
	return out, err
}

// Logout invalidates the session and clears the local token.
func (s *AuthService) Logout(ctx context.Context) (map[string]any, error) {
	var out map[string]any
	err := s.client.postJSON(ctx, "/auth/logout", "session", nil, &out)
	s.client.sessionToken = ""
	return out, err
}

// --- oauth -------------------------------------------------------------------

// PKCEPair is a PKCE verifier/challenge pair.
type PKCEPair struct {
	Verifier  string
	Challenge string
	Method    string
}

// CreatePKCEPair generates a PKCE verifier/challenge pair (S256).
func CreatePKCEPair() (PKCEPair, error) {
	buf := make([]byte, 32)
	if _, err := rand.Read(buf); err != nil {
		return PKCEPair{}, err
	}
	verifier := base64.RawURLEncoding.EncodeToString(buf)
	sum := sha256.Sum256([]byte(verifier))
	return PKCEPair{
		Verifier:  verifier,
		Challenge: base64.RawURLEncoding.EncodeToString(sum[:]),
		Method:    "S256",
	}, nil
}

// AuthorizeParams are the inputs to OAuth.AuthorizeURL.
type AuthorizeParams struct {
	ClientID            string
	RedirectURI         string
	Scope               []string
	State               string
	CodeChallenge       string
	CodeChallengeMethod string
}

// OAuthService provides the OAuth 2.0 provider flow + app management.
type OAuthService struct{ client *Client }

// AuthorizeURL builds the /oauth/authorize URL to redirect a user to.
func (s *OAuthService) AuthorizeURL(p AuthorizeParams) string {
	q := url.Values{
		"response_type": {"code"},
		"client_id":     {p.ClientID},
		"redirect_uri":  {p.RedirectURI},
	}
	if len(p.Scope) > 0 {
		q.Set("scope", strings.Join(p.Scope, " "))
	}
	if p.State != "" {
		q.Set("state", p.State)
	}
	if p.CodeChallenge != "" {
		q.Set("code_challenge", p.CodeChallenge)
		method := p.CodeChallengeMethod
		if method == "" {
			method = "S256"
		}
		q.Set("code_challenge_method", method)
	}
	return s.client.baseURL + "/oauth/authorize?" + q.Encode()
}

// ExchangeToken exchanges an authorization code for an access token.
func (s *OAuthService) ExchangeToken(ctx context.Context, params map[string]string) (map[string]any, error) {
	form := url.Values{"grant_type": {"authorization_code"}}
	for k, v := range params {
		if v != "" {
			form.Set(k, v)
		}
	}
	o := requestOptions{auth: "none", body: []byte(form.Encode()), contentType: "application/x-www-form-urlencoded"}
	var out map[string]any
	err := s.client.requestJSON(ctx, http.MethodPost, "/oauth/token", o, &out)
	return out, err
}

// UserInfo returns the profile for an access token.
func (s *OAuthService) UserInfo(ctx context.Context, accessToken string) (map[string]any, error) {
	o := requestOptions{auth: "none", headers: map[string]string{"authorization": "Bearer " + accessToken}}
	var out map[string]any
	err := s.client.requestJSON(ctx, http.MethodGet, "/oauth/userinfo", o, &out)
	return out, err
}

// RevokeToken revokes an access token.
func (s *OAuthService) RevokeToken(ctx context.Context, token string) error {
	form := url.Values{"token": {token}}
	o := requestOptions{auth: "none", body: []byte(form.Encode()), contentType: "application/x-www-form-urlencoded"}
	return s.client.requestJSON(ctx, http.MethodPost, "/oauth/revoke", o, nil)
}

// ListApps lists OAuth apps the caller owns.
func (s *OAuthService) ListApps(ctx context.Context) (map[string]any, error) {
	var out map[string]any
	err := s.client.getJSON(ctx, "/api/me/oauth-apps", "session", nil, &out)
	return out, err
}

// CreateApp registers a new OAuth app.
func (s *OAuthService) CreateApp(ctx context.Context, params map[string]any) (map[string]any, error) {
	var out map[string]any
	err := s.client.postJSON(ctx, "/api/me/oauth-apps", "session", params, &out)
	return out, err
}

// GetApp returns one owned OAuth app.
func (s *OAuthService) GetApp(ctx context.Context, clientID string) (map[string]any, error) {
	var out map[string]any
	err := s.client.getJSON(ctx, "/api/me/oauth-apps/"+url.PathEscape(clientID), "session", nil, &out)
	return out, err
}

// UpdateApp updates an OAuth app.
func (s *OAuthService) UpdateApp(ctx context.Context, clientID string, patch map[string]any) (map[string]any, error) {
	var out map[string]any
	err := s.client.postJSONMethod(ctx, http.MethodPatch, "/api/me/oauth-apps/"+url.PathEscape(clientID), "session", patch, &out)
	return out, err
}

// DeleteApp deletes an OAuth app.
func (s *OAuthService) DeleteApp(ctx context.Context, clientID string) error {
	return s.client.deleteJSON(ctx, "/api/me/oauth-apps/"+url.PathEscape(clientID), "session", nil)
}

// RotateSecret rotates an OAuth app's client secret.
func (s *OAuthService) RotateSecret(ctx context.Context, clientID string) (map[string]any, error) {
	var out map[string]any
	err := s.client.postJSON(ctx, "/api/me/oauth-apps/"+url.PathEscape(clientID)+"/rotate-secret", "session", nil, &out)
	return out, err
}

// ConnectedApps lists apps the caller has authorized.
func (s *OAuthService) ConnectedApps(ctx context.Context) (map[string]any, error) {
	var out map[string]any
	err := s.client.getJSON(ctx, "/api/me/connected-apps", "session", nil, &out)
	return out, err
}

// RevokeConnectedApp revokes all tokens granted to a connected app.
func (s *OAuthService) RevokeConnectedApp(ctx context.Context, clientID string) (map[string]any, error) {
	var out map[string]any
	err := s.client.deleteJSON(ctx, "/api/me/connected-apps/"+url.PathEscape(clientID), "session", &out)
	return out, err
}
