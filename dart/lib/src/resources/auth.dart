import 'dart:convert';
import 'dart:math';

import 'package:crypto/crypto.dart';

import '../transport.dart';

String _enc(String s) => Uri.encodeComponent(s);

/// Generate a PKCE verifier/challenge pair (S256).
({String verifier, String challenge, String method}) createPkcePair() {
  final rnd = Random.secure();
  final bytes = List<int>.generate(32, (_) => rnd.nextInt(256));
  final verifier = base64UrlEncode(bytes).replaceAll('=', '');
  final challenge = base64UrlEncode(sha256.convert(utf8.encode(verifier)).bytes).replaceAll('=', '');
  return (verifier: verifier, challenge: challenge, method: 'S256');
}

/// Two-factor authentication — `/api/2fa/*`.
class TwoFactor {
  final Transport _t;
  TwoFactor(this._t);

  Future<dynamic> setupInit() => _t.post('/api/2fa/setup-init', 'session');
  Future<dynamic> setupVerify(String code) => _t.post('/api/2fa/setup-verify', 'session', {'code': code});
  Future<dynamic> disable(String password, String code) =>
      _t.post('/api/2fa/disable', 'session', {'password': password, 'code': code});
  Future<dynamic> regenerateBackupCodes(String code) =>
      _t.post('/api/2fa/regenerate-backup-codes', 'session', {'code': code});
  Future<dynamic> verifyStepUp(String code) => _t.post('/api/2fa/verify-step-up', 'session', {'code': code});
  Future<dynamic> stepUpStatus() => _t.get('/api/2fa/step-up-status', 'session');
}

/// Authentication — `/auth/*`. Login/signup adopt the session token automatically.
class Auth {
  final Transport _t;
  Auth(this._t);

  Future<dynamic> _submit(String path, Object? body, [Map<String, String>? headers]) async {
    final (json, cookie) = await _t.requestJsonCookie(path, body, headers);
    if (cookie != null) {
      _t.setSessionToken(cookie);
      if (json is Map) json['session_token'] = cookie;
    }
    return json;
  }

  Future<dynamic> signup(Map<String, dynamic> request) => _submit('/auth/signup', request);

  Future<dynamic> signupPrecheck(Map<String, dynamic> request) =>
      _t.post('/auth/signup/precheck', 'none', request);

  Future<dynamic> login(String username, String password, String captchaToken) =>
      _submit('/auth/login', {'username': username, 'password': password, 'captcha_token': captchaToken});

  Future<dynamic> verify2fa(String challengeToken, String code, {String? backupCode}) => _submit(
      '/auth/2fa/verify',
      {'code': code, if (backupCode != null) 'backup_code': backupCode},
      {'authorization': 'Bearer $challengeToken'});

  Future<dynamic> verifyEmail(String token) => _t.post('/auth/verify', 'none', {'token': token});

  Future<dynamic> resendVerification(String identifier) =>
      _t.post('/auth/resend-verification', 'none', {'identifier': identifier});

  Future<dynamic> logout() async {
    final result = await _t.post('/auth/logout', 'session');
    _t.setSessionToken(null);
    return result;
  }
}

/// OAuth 2.0 provider flow + self-service app management.
class OAuth {
  final Transport _t;
  OAuth(this._t);

  String authorizeUrl({
    required String clientId,
    required String redirectUri,
    List<String>? scope,
    String? state,
    String? codeChallenge,
    String codeChallengeMethod = 'S256',
  }) {
    final q = {
      'response_type': 'code',
      'client_id': clientId,
      'redirect_uri': redirectUri,
      if (scope != null && scope.isNotEmpty) 'scope': scope.join(' '),
      if (state != null) 'state': state,
      if (codeChallenge != null) 'code_challenge': codeChallenge,
      if (codeChallenge != null) 'code_challenge_method': codeChallengeMethod,
    };
    return '${_t.baseUrl}/oauth/authorize?${Uri(queryParameters: q).query}';
  }

  Future<dynamic> exchangeToken(Map<String, String> params) =>
      _t.form('/oauth/token', Uri(queryParameters: {'grant_type': 'authorization_code', ...params}).query);

  Future<dynamic> userInfo(String accessToken) =>
      _t.getWithHeader('/oauth/userinfo', {'authorization': 'Bearer $accessToken'});

  Future<dynamic> revokeToken(String token) =>
      _t.form('/oauth/revoke', Uri(queryParameters: {'token': token}).query);

  Future<dynamic> listApps() => _t.get('/api/me/oauth-apps', 'session');
  Future<dynamic> createApp(Map<String, dynamic> request) => _t.post('/api/me/oauth-apps', 'session', request);
  Future<dynamic> getApp(String clientId) => _t.get('/api/me/oauth-apps/${_enc(clientId)}', 'session');
  Future<dynamic> updateApp(String clientId, Map<String, dynamic> patch) =>
      _t.method('PATCH', '/api/me/oauth-apps/${_enc(clientId)}', 'session', patch);
  Future<dynamic> deleteApp(String clientId) => _t.delete('/api/me/oauth-apps/${_enc(clientId)}', 'session');
  Future<dynamic> rotateSecret(String clientId) =>
      _t.post('/api/me/oauth-apps/${_enc(clientId)}/rotate-secret', 'session');
  Future<dynamic> connectedApps() => _t.get('/api/me/connected-apps', 'session');
  Future<dynamic> revokeConnectedApp(String clientId) =>
      _t.delete('/api/me/connected-apps/${_enc(clientId)}', 'session');
}
