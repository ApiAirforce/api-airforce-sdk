import '../transport.dart';

String _enc(String s) => Uri.encodeComponent(s);

/// Account self-service — `/api/me`, `/api/user/*`.
class Account {
  final Transport _t;
  Account(this._t);

  Future<dynamic> me() => _t.get('/api/me', 'session');
  Future<dynamic> usage() => _t.get('/api/usage', 'session');
  Future<dynamic> myUsage() => _t.get('/api/my-usage', 'session');

  Future<dynamic> update(Map<String, dynamic> body) => _t.method('PUT', '/api/user/update', 'session', body);

  Future<dynamic> requestPasswordReset(String email, {String? locale}) => _t.post(
      '/api/auth/request-password-reset', 'none', {'email': email, if (locale != null) 'locale': locale});

  Future<dynamic> resetPassword(String token, String newPassword) =>
      _t.post('/api/auth/reset-password', 'none', {'token': token, 'new_password': newPassword});

  Future<dynamic> referralCode() => _t.get('/api/referral/code', 'session');
  Future<dynamic> referredUsers() => _t.get('/api/referral/referred-users', 'session');

  Future<dynamic> getPriceCaps() => _t.get('/api/user/price-caps', 'session');
  Future<dynamic> setPriceCaps(Map<String, dynamic> caps) =>
      _t.method('PUT', '/api/user/price-caps', 'session', {'caps': caps});
  Future<dynamic> deletePriceCap(String model) =>
      _t.delete('/api/user/price-caps/${_enc(model)}', 'session');

  Future<dynamic> getModelAliases() => _t.get('/api/user/model-aliases', 'session');
  Future<dynamic> setModelAlias(String alias, String model) =>
      _t.method('PUT', '/api/user/model-aliases', 'session', {'alias': alias, 'model': model});
  Future<dynamic> setModelAliasesBatch(List<Map<String, String>> aliases) =>
      _t.method('PUT', '/api/user/model-aliases/batch', 'session', aliases);
  Future<dynamic> deleteModelAlias(String alias) =>
      _t.delete('/api/user/model-aliases/${_enc(alias)}', 'session');

  Future<dynamic> getModelDefaults() => _t.get('/api/user/model-defaults', 'session');
  Future<dynamic> setModelDefault(String model, Map<String, dynamic> def) =>
      _t.method('PUT', '/api/user/model-defaults/${_enc(model)}', 'session', def);
  Future<dynamic> deleteModelDefault(String model) =>
      _t.delete('/api/user/model-defaults/${_enc(model)}', 'session');

  Future<dynamic> getSmartRouting() => _t.get('/api/user/smart-routing', 'api_key');
  Future<dynamic> setSmartRouting(Map<String, dynamic> groups) =>
      _t.method('PUT', '/api/user/smart-routing', 'api_key', {'groups': groups});
  Future<dynamic> testSmartRouting(String model) =>
      _t.get('/api/user/smart-routing/test', 'api_key', query: {'model': model});

  Future<dynamic> getChannelPrefs() => _t.get('/api/user/channel-prefs', 'api_key');
  Future<dynamic> setChannelPins(Map<String, dynamic> pins) =>
      _t.method('PUT', '/api/user/channel-prefs', 'api_key', pins);

  Future<dynamic> sessions() => _t.get('/api/me/sessions', 'session');
  Future<dynamic> revokeSession(String jti) => _t.delete('/api/me/sessions/${_enc(jti)}', 'session');
  Future<dynamic> revokeOtherSessions() => _t.delete('/api/me/sessions', 'session');

  Future<dynamic> loginHistory({int? limit}) =>
      _t.get('/api/me/login-history', 'session', query: limit != null ? {'limit': '$limit'} : null);

  Future<dynamic> resetApiKey() => _t.post('/api/user/reset-api-key', 'session');
  Future<dynamic> setPrimaryAllowedIps(List<String> ips) =>
      _t.method('PUT', '/api/user/primary-allowed-ips', 'session', {'allowed_ips': ips});
  Future<dynamic> setBackupPoolEnabled(bool enabled) =>
      _t.method('PUT', '/api/user/backup-pool-enabled', 'api_key', {'enabled': enabled});
  Future<dynamic> togglePayAsYouGo() => _t.post('/api/pay-as-you-go/toggle', 'session');
}

/// API key provisioning — `/v1/keys`.
class Keys {
  final Transport _t;
  Keys(this._t);

  Future<dynamic> create(Map<String, dynamic> request) => _t.post('/v1/keys', 'api_key', request);
  Future<dynamic> list() async {
    final res = await _t.get('/v1/keys', 'api_key');
    return res is Map && res.containsKey('keys') ? res['keys'] : res;
  }
  Future<dynamic> update(String key, Map<String, dynamic> request) =>
      _t.method('PATCH', '/v1/keys/${_enc(key)}', 'api_key', request);
  Future<dynamic> delete(String key) => _t.delete('/v1/keys/${_enc(key)}', 'api_key');
}

/// Billing, plans, and public analytics.
class Billing {
  final Transport _t;
  Billing(this._t);

  Future<dynamic> createCheckout(Map<String, dynamic> request) =>
      _t.post('/api/creem/create-checkout', 'session', request);
  Future<dynamic> createCryptoInvoice(Map<String, dynamic> request) =>
      _t.post('/api/create-nowpayments-invoice', 'session', request);
  Future<dynamic> createPortalSession() =>
      _t.post('/api/create-portal-session', 'session', <String, dynamic>{});
  Future<dynamic> analytics() => _t.get('/v1/analytics', 'none');
}
