import 'package:http/http.dart' as http;

import 'resources/account.dart';
import 'resources/auth.dart';
import 'resources/catalog.dart';
import 'resources/inference.dart';
import 'resources/media.dart';
import 'transport.dart';

/// The api.airforce API client.
///
/// ```dart
/// final client = AirforceClient(apiKey: 'sk-air-...');
/// final res = await client.chat.create({
///   'model': 'claude-opus-4.8',
///   'messages': [{'role': 'user', 'content': 'Hello!'}],
/// });
/// ```
class AirforceClient {
  final Transport _t;

  late final Chat chat;
  late final Messages messages;
  late final Responses responses;
  late final Gemini gemini;
  late final Models models;
  late final Images images;
  late final Audio audio;
  late final Video video;
  late final Voices voices;
  late final Account account;
  late final Keys keys;
  late final Billing billing;
  late final TwoFactor twofa;
  late final Auth auth;
  late final OAuth oauth;

  AirforceClient._(this._t) {
    chat = Chat(_t);
    messages = Messages(_t);
    responses = Responses(_t);
    gemini = Gemini(_t);
    models = Models(_t);
    images = Images(_t);
    audio = Audio(_t);
    video = Video(_t);
    voices = Voices(_t);
    account = Account(_t);
    keys = Keys(_t);
    billing = Billing(_t);
    twofa = TwoFactor(_t);
    auth = Auth(_t);
    oauth = OAuth(_t);
  }

  factory AirforceClient({
    String? apiKey,
    String? sessionToken,
    String? baseUrl,
    Duration timeout = const Duration(seconds: 60),
    int maxRetries = 2,
    Map<String, String>? defaultHeaders,
    http.Client? httpClient,
  }) {
    final transport = Transport(
      http: httpClient ?? http.Client(),
      apiKey: apiKey,
      sessionToken: sessionToken,
      baseUrl: (baseUrl ?? 'https://api.airforce').replaceAll(RegExp(r'/+$'), ''),
      timeout: timeout,
      maxRetries: maxRetries,
      defaultHeaders: defaultHeaders ?? {},
    );
    return AirforceClient._(transport);
  }

  String get baseUrl => _t.baseUrl;

  /// Set the session token (e.g. a JWT obtained elsewhere).
  void setSessionToken(String? token) => _t.setSessionToken(token);

  /// Close the underlying HTTP client.
  void close() => _t.close();
}
