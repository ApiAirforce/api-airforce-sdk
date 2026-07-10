package airforce

import (
	"context"
	"net/http"
	"net/url"
	"strconv"
)

// NotificationsService accesses notification preferences, the in-app feed and
// delivery-channel linking under /api/me/*. All endpoints require a session
// token.
type NotificationsService struct{ client *Client }

// GetPrefs returns the caller's notification preferences.
func (s *NotificationsService) GetPrefs(ctx context.Context) (map[string]any, error) {
	var out map[string]any
	err := s.client.getJSON(ctx, "/api/me/notification-prefs", "session", nil, &out)
	return out, err
}

// UpdatePrefs partially updates the preferences: absent fields stay unchanged,
// "quiet_hours": nil clears quiet hours, unknown channel ids in routing are
// dropped server-side. Returns the updated preferences.
func (s *NotificationsService) UpdatePrefs(ctx context.Context, patch map[string]any) (map[string]any, error) {
	var out map[string]any
	err := s.client.postJSONMethod(ctx, http.MethodPatch, "/api/me/notification-prefs", "session", patch, &out)
	return out, err
}

// List returns the in-app feed, newest first, as {items, unread}. limit is
// 1-100 (0 = server default of 30); before is a created_at cursor for paging
// (empty = start at the newest item).
func (s *NotificationsService) List(ctx context.Context, limit int, before string) (map[string]any, error) {
	query := url.Values{}
	if limit > 0 {
		query.Set("limit", strconv.Itoa(limit))
	}
	if before != "" {
		query.Set("before", before)
	}
	if len(query) == 0 {
		query = nil
	}
	var out map[string]any
	err := s.client.getJSON(ctx, "/api/me/notifications", "session", query, &out)
	return out, err
}

// MarkRead marks feed items read by ids, or everything when all is true.
// Returns {updated, unread}.
func (s *NotificationsService) MarkRead(ctx context.Context, ids []string, all bool) (map[string]any, error) {
	body := map[string]any{}
	if len(ids) > 0 {
		body["ids"] = ids
	}
	if all {
		body["all"] = true
	}
	var out map[string]any
	err := s.client.postJSON(ctx, "/api/me/notifications/read", "session", body, &out)
	return out, err
}

// Channels lists linked delivery-channel identities plus the linkable channel
// ids ({identities, available_channels}).
func (s *NotificationsService) Channels(ctx context.Context) (map[string]any, error) {
	var out map[string]any
	err := s.client.getJSON(ctx, "/api/me/channels", "session", nil, &out)
	return out, err
}

// LinkChannel starts linking a delivery channel. The verification code is
// delivered through the channel itself (30-minute expiry); bot channels accept
// an empty address and return a one-time link code / deep link instead
// ({status: "link_ready", code, deep_link?, expires_minutes}).
func (s *NotificationsService) LinkChannel(ctx context.Context, channel, address, display string) (map[string]any, error) {
	body := map[string]any{"channel": channel, "address": address}
	if display != "" {
		body["display"] = display
	}
	var out map[string]any
	err := s.client.postJSON(ctx, "/api/me/channels", "session", body, &out)
	return out, err
}

// VerifyChannel completes channel verification with the delivered code
// (400 on an invalid or expired code).
func (s *NotificationsService) VerifyChannel(ctx context.Context, channel, code string) (map[string]any, error) {
	var out map[string]any
	err := s.client.postJSON(ctx, "/api/me/channels/verify", "session", map[string]any{"channel": channel, "code": code}, &out)
	return out, err
}

// UnlinkChannel revokes a linked channel identity.
func (s *NotificationsService) UnlinkChannel(ctx context.Context, channel string) (map[string]any, error) {
	var out map[string]any
	err := s.client.deleteJSON(ctx, "/api/me/channels/"+url.PathEscape(channel), "session", &out)
	return out, err
}
