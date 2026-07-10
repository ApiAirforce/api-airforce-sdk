import '../transport.dart';

String _enc(String s) => Uri.encodeComponent(s);

/// Organization self-service — `/api/org/*`.
///
/// All endpoints require a session token. The org context is implicit via the
/// caller's membership (one org per user); roles are `owner` ⊃ `admin` ⊃
/// `member`. Callers without an org get a 404 `no_org`; suspended members get
/// 403 `membership_inactive`.
class Org {
  final Transport _t;
  Org(this._t);

  /// The caller's org + own role → `{org: Org, role}`.
  Future<dynamic> get() => _t.get('/api/org', 'session');

  /// Rename the org (owner only; name 1–100 chars).
  Future<dynamic> rename(String name) =>
      _t.method('PATCH', '/api/org', 'session', {'name': name});

  /// Owner-only SSO config — `{tenant_id?, verified_domain?, enforced?}`.
  /// `''` clears a field; omitted fields are unchanged. 409 when the tenant
  /// or domain is already claimed by another org.
  Future<dynamic> updateSso(Map<String, dynamic> patch) =>
      _t.method('PATCH', '/api/org/sso', 'session', patch);

  /// List members (owner/admin only).
  Future<dynamic> members() async {
    final res = await _t.get('/api/org/members', 'session');
    return res is Map && res.containsKey('members') ? res['members'] : res;
  }

  /// Change a member's role (owner only) and/or status — suspending disables
  /// the member's org keys. The owner row is immutable; admins may only
  /// manage plain members.
  Future<dynamic> updateMember(String userId, Map<String, dynamic> patch) =>
      _t.method('PATCH', '/api/org/members/${_enc(userId)}', 'session', patch);

  /// Remove a member (owner/admin) or leave the org (self). The removed
  /// member's org keys are disabled.
  Future<dynamic> removeMember(String userId) =>
      _t.delete('/api/org/members/${_enc(userId)}', 'session');

  /// List pending invites (owner/admin).
  Future<dynamic> invites() async {
    final res = await _t.get('/api/org/invites', 'session');
    return res is Map && res.containsKey('invites') ? res['invites'] : res;
  }

  /// Invite by email (7-day expiry) → `{invite, invite_url}`. Admin invites
  /// are owner-only; mail delivery is best-effort — `invite_url` is the
  /// reliable path.
  Future<dynamic> createInvite(String email, {String? role}) =>
      _t.post('/api/org/invites', 'session',
          {'email': email, if (role != null) 'role': role});

  /// Accept an invite (any logged-in user without an org) → `{org, role}`.
  /// The caller's email must match the invite and be verified.
  Future<dynamic> acceptInvite(String token) =>
      _t.post('/api/org/invites/accept', 'session', {'token': token});

  /// Revoke a pending invite (owner/admin).
  Future<dynamic> revokeInvite(String id) =>
      _t.delete('/api/org/invites/${_enc(id)}', 'session');

  /// List org keys — owner/admin: all; member: own only. Keys are masked.
  Future<dynamic> keys() async {
    final res = await _t.get('/api/org/keys', 'session');
    return res is Map && res.containsKey('keys') ? res['keys'] : res;
  }

  /// Create a key for a member (owner/admin) — `{member_user_id, label?,
  /// credit_allowance?, limit_reset?, rpm_limit?, allowed_models?, ...}`.
  /// Bills the org owner's wallet; the full key is shown only in this
  /// response.
  Future<dynamic> createKey(Map<String, dynamic> request) async {
    final res = await _t.post('/api/org/keys', 'session', request);
    return res is Map && res.containsKey('item') ? res['item'] : res;
  }

  /// Update an org key (owner/admin); same fields as create plus `disabled`
  /// (`member_user_id` is not changeable). Returns the masked key.
  Future<dynamic> updateKey(String id, Map<String, dynamic> patch) async {
    final res = await _t.method('PATCH', '/api/org/keys/${_enc(id)}', 'session', patch);
    return res is Map && res.containsKey('item') ? res['item'] : res;
  }

  /// Delete an org key (owner/admin).
  Future<dynamic> deleteKey(String id) => _t.delete('/api/org/keys/${_enc(id)}', 'session');

  /// Aggregate + per-member + per-key + daily timeseries usage. `from`/`to`
  /// are unix seconds (default: last 30 days); cost values are cents. Plain
  /// members see only their own usage.
  Future<dynamic> usage({int? from, int? to, String? memberUserId, String? keyId}) =>
      _t.get('/api/org/usage', 'session', query: {
        if (from != null) 'from': '$from',
        if (to != null) 'to': '$to',
        if (memberUserId != null) 'member_user_id': memberUserId,
        if (keyId != null) 'key_id': keyId,
      });
}
