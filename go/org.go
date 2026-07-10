package airforce

import (
	"context"
	"net/http"
	"net/url"
	"strconv"
)

// OrgService accesses the organization self-service surface under /api/org/*.
// All endpoints require a session token; the org context is implicit via the
// caller's membership (one org per user). Roles: owner > admin > member.
// Callers without an org get 404 no_org; suspended members get
// 403 membership_inactive everywhere.
type OrgService struct{ client *Client }

func orgMemberPath(userID int64) string {
	return "/api/org/members/" + strconv.FormatInt(userID, 10)
}

// Get returns the caller's org and their own role ({org, role}).
func (s *OrgService) Get(ctx context.Context) (map[string]any, error) {
	var out map[string]any
	err := s.client.getJSON(ctx, "/api/org", "session", nil, &out)
	return out, err
}

// Update renames the org (owner only; name 1-100 chars).
func (s *OrgService) Update(ctx context.Context, params map[string]any) (map[string]any, error) {
	var out map[string]any
	err := s.client.postJSONMethod(ctx, http.MethodPatch, "/api/org", "session", params, &out)
	return out, err
}

// UpdateSSO configures org SSO (owner only). An empty string clears a field;
// omitted fields stay unchanged. 409 tenant_already_claimed /
// domain_already_claimed on uniqueness conflicts.
func (s *OrgService) UpdateSSO(ctx context.Context, params map[string]any) (map[string]any, error) {
	var out map[string]any
	err := s.client.postJSONMethod(ctx, http.MethodPatch, "/api/org/sso", "session", params, &out)
	return out, err
}

// Members lists org members (owner/admin only).
func (s *OrgService) Members(ctx context.Context) ([]map[string]any, error) {
	var out struct {
		Members []map[string]any `json:"members"`
	}
	err := s.client.getJSON(ctx, "/api/org/members", "session", nil, &out)
	return out.Members, err
}

// UpdateMember changes a member's role (owner only) and/or status. Suspending
// disables the member's org keys; the owner row is immutable; admins may only
// manage plain members.
func (s *OrgService) UpdateMember(ctx context.Context, userID int64, params map[string]any) (map[string]any, error) {
	var out map[string]any
	err := s.client.postJSONMethod(ctx, http.MethodPatch, orgMemberPath(userID), "session", params, &out)
	return out, err
}

// RemoveMember removes a member (owner/admin) or leaves the org (self). The
// owner cannot be removed; the member's org keys are disabled.
func (s *OrgService) RemoveMember(ctx context.Context, userID int64) (map[string]any, error) {
	var out map[string]any
	err := s.client.deleteJSON(ctx, orgMemberPath(userID), "session", &out)
	return out, err
}

// Invites lists pending invites (owner/admin).
func (s *OrgService) Invites(ctx context.Context) ([]map[string]any, error) {
	var out struct {
		Invites []map[string]any `json:"invites"`
	}
	err := s.client.getJSON(ctx, "/api/org/invites", "session", nil, &out)
	return out.Invites, err
}

// CreateInvite invites a user by email (7-day expiry). role defaults to
// "member" when empty; "admin" invites are owner-only. The invite mail is
// best-effort — the returned invite_url is the reliable path. 429 on
// invite_cooldown / invite_cap_reached.
func (s *OrgService) CreateInvite(ctx context.Context, email, role string) (map[string]any, error) {
	body := map[string]any{"email": email}
	if role != "" {
		body["role"] = role
	}
	var out map[string]any
	err := s.client.postJSON(ctx, "/api/org/invites", "session", body, &out)
	return out, err
}

// AcceptInvite accepts an invite token (any logged-in user without an org).
// The caller's email must match the invite and be verified; 409
// already_in_org, 410 expired.
func (s *OrgService) AcceptInvite(ctx context.Context, token string) (map[string]any, error) {
	var out map[string]any
	err := s.client.postJSON(ctx, "/api/org/invites/accept", "session", map[string]any{"token": token}, &out)
	return out, err
}

// RevokeInvite revokes a pending invite (owner/admin).
func (s *OrgService) RevokeInvite(ctx context.Context, id string) (map[string]any, error) {
	var out map[string]any
	err := s.client.deleteJSON(ctx, "/api/org/invites/"+url.PathEscape(id), "session", &out)
	return out, err
}

// Keys lists org keys — owner/admin see all, members only their own. Key
// material is masked (masked_key / key_prefix / key_last4).
func (s *OrgService) Keys(ctx context.Context) ([]map[string]any, error) {
	var out struct {
		Keys []map[string]any `json:"keys"`
	}
	err := s.client.getJSON(ctx, "/api/org/keys", "session", nil, &out)
	return out.Keys, err
}

// CreateKey creates an org key for a member (owner/admin); params must carry
// member_user_id and may carry label, credit_allowance, limit_reset,
// rpm_limit and the allow/block scoping lists. The key bills the org owner's
// wallet; the full key material is returned only here.
func (s *OrgService) CreateKey(ctx context.Context, params map[string]any) (map[string]any, error) {
	var out map[string]any
	err := s.client.postJSON(ctx, "/api/org/keys", "session", params, &out)
	return out, err
}

// UpdateKey updates an org key (owner/admin); same fields as CreateKey plus
// disabled (member_user_id is not changeable). Only org-marked keys are
// reachable — the owner's private keys are not.
func (s *OrgService) UpdateKey(ctx context.Context, id string, params map[string]any) (map[string]any, error) {
	var out map[string]any
	err := s.client.postJSONMethod(ctx, http.MethodPatch, "/api/org/keys/"+url.PathEscape(id), "session", params, &out)
	return out, err
}

// DeleteKey deletes an org key (owner/admin).
func (s *OrgService) DeleteKey(ctx context.Context, id string) error {
	return s.client.deleteJSON(ctx, "/api/org/keys/"+url.PathEscape(id), "session", nil)
}

// Usage returns aggregate + per-member + per-key + daily-timeseries usage.
// from/to are unix seconds (0 = server default of the last 30 days);
// memberUserID (0 = all) and keyID ("" = all) filter optionally. Members are
// scoped to themselves; cost values are cents.
func (s *OrgService) Usage(ctx context.Context, from, to int64, memberUserID int64, keyID string) (map[string]any, error) {
	query := url.Values{}
	if from > 0 {
		query.Set("from", strconv.FormatInt(from, 10))
	}
	if to > 0 {
		query.Set("to", strconv.FormatInt(to, 10))
	}
	if memberUserID > 0 {
		query.Set("member_user_id", strconv.FormatInt(memberUserID, 10))
	}
	if keyID != "" {
		query.Set("key_id", keyID)
	}
	if len(query) == 0 {
		query = nil
	}
	var out map[string]any
	err := s.client.getJSON(ctx, "/api/org/usage", "session", query, &out)
	return out, err
}
