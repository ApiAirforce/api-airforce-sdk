import '../transport.dart';

String _enc(String s) => Uri.encodeComponent(s);

/// Notifications — preferences, the in-app feed, and delivery-channel
/// linking (`/api/me/notification-prefs`, `/api/me/notifications`,
/// `/api/me/channels`). All endpoints require a session token.
class Notifications {
  final Transport _t;
  Notifications(this._t);

  /// The caller's notification preferences.
  Future<dynamic> getPrefs() => _t.get('/api/me/notification-prefs', 'session');

  /// Partial update — absent fields are unchanged; `'quiet_hours': null`
  /// clears quiet hours. Returns the updated preferences.
  Future<dynamic> updatePrefs(Map<String, dynamic> patch) =>
      _t.method('PATCH', '/api/me/notification-prefs', 'session', patch);

  /// In-app feed, newest first → `{items: [FeedItem], unread}`.
  /// `limit` is 1–100 (default 30); `before` is a `created_at` cursor for
  /// paging.
  Future<dynamic> list({int? limit, String? before}) =>
      _t.get('/api/me/notifications', 'session', query: {
        if (limit != null) 'limit': '$limit',
        if (before != null) 'before': before,
      });

  /// Mark feed items read, by ids or all → `{updated, unread}`.
  Future<dynamic> markRead({List<String>? ids, bool all = false}) =>
      _t.post('/api/me/notifications/read', 'session',
          {if (ids != null) 'ids': ids, if (all) 'all': true});

  /// Linked delivery-channel identities + linkable channel ids →
  /// `{identities: [ChannelIdentity], available_channels: [string]}`.
  Future<dynamic> channels() => _t.get('/api/me/channels', 'session');

  /// Start linking a channel. The verification code is delivered through the
  /// channel itself and expires after 30 minutes. Bot channels may pass an
  /// empty `address` and get `{status: 'link_ready', code, deep_link?}`
  /// instead of `{status: 'verification_sent'}`.
  Future<dynamic> addChannel(String channel, String address, {String? display}) =>
      _t.post('/api/me/channels', 'session',
          {'channel': channel, 'address': address, if (display != null) 'display': display});

  /// Complete channel verification with the delivered code.
  Future<dynamic> verifyChannel(String channel, String code) =>
      _t.post('/api/me/channels/verify', 'session', {'channel': channel, 'code': code});

  /// Unlink/revoke a channel identity.
  Future<dynamic> removeChannel(String channel) =>
      _t.delete('/api/me/channels/${_enc(channel)}', 'session');
}
