import 'dart:async';
import 'dart:convert';
import 'dart:math';

import 'package:http/http.dart' as http;

import 'exceptions.dart';
import 'sse.dart';

const sdkVersion = '0.0.1';
// 409 is excluded: a terminal business conflict, not transient.
const _retryable = {408, 429, 500, 502, 503, 504};

typedef MultipartFile = ({String field, String filename, List<int> data});

({List<int> body, String contentType}) buildMultipart(
    Map<String, String> fields, List<MultipartFile> files) {
  final boundary = 'airforceBoundary${DateTime.now().microsecondsSinceEpoch}${Random().nextInt(1 << 32)}';
  final body = <int>[];
  void write(String s) => body.addAll(utf8.encode(s));

  fields.forEach((key, value) {
    write('--$boundary\r\nContent-Disposition: form-data; name="$key"\r\n\r\n$value\r\n');
  });
  for (final file in files) {
    write('--$boundary\r\nContent-Disposition: form-data; name="${file.field}"; '
        'filename="${file.filename}"\r\nContent-Type: application/octet-stream\r\n\r\n');
    body.addAll(file.data);
    write('\r\n');
  }
  write('--$boundary--\r\n');
  return (body: body, contentType: 'multipart/form-data; boundary=$boundary');
}

class Transport {
  final http.Client _http;
  final String? _apiKey;
  String? _sessionToken;
  final String baseUrl;
  final Duration timeout;
  final int maxRetries;
  final Map<String, String> defaultHeaders;

  Transport({
    required http.Client http,
    String? apiKey,
    String? sessionToken,
    required this.baseUrl,
    required this.timeout,
    required this.maxRetries,
    required this.defaultHeaders,
  })  : _http = http,
        _apiKey = apiKey,
        _sessionToken = sessionToken;

  void setSessionToken(String? token) => _sessionToken = token;

  void close() => _http.close();

  String? _resolveToken(String auth) {
    if (auth == 'none') return null;
    // Session endpoints require a session JWT — never substitute an API key.
    final token = auth == 'session' ? _sessionToken : (_apiKey ?? _sessionToken);
    if (token == null) {
      throw MissingCredentialException(auth == 'session'
          ? 'This endpoint requires a session token (set sessionToken / auth.login()).'
          : 'This endpoint requires an API key (set apiKey).');
    }
    return token;
  }

  Future<http.StreamedResponse> _send(
    String method,
    String path, {
    required String auth,
    Map<String, String>? query,
    List<int>? body,
    String? contentType,
    Map<String, String>? extraHeaders,
    bool stream = false,
  }) async {
    final token = _resolveToken(auth);
    var uri = Uri.parse('$baseUrl${path.startsWith('/') ? path : '/$path'}');
    if (query != null && query.isNotEmpty) {
      uri = uri.replace(queryParameters: {...uri.queryParameters, ...query});
    }

    var attempt = 0;
    while (true) {
      final request = http.Request(method, uri);
      request.headers['user-agent'] = 'airforce-sdk-dart/$sdkVersion';
      request.headers['x-airforce-sdk'] = 'dart/$sdkVersion';
      request.headers['accept'] = stream ? 'text/event-stream' : 'application/json';
      if (token != null) request.headers['authorization'] = 'Bearer $token';
      defaultHeaders.forEach((k, v) => request.headers[k] = v);
      extraHeaders?.forEach((k, v) => request.headers[k] = v);
      if (body != null) {
        request.bodyBytes = body;
        if (contentType != null) request.headers['content-type'] = contentType;
      }

      http.StreamedResponse resp;
      try {
        resp = await _http.send(request).timeout(timeout);
      } on TimeoutException {
        if (_canRetryTransport(method, attempt)) {
          await _backoff(++attempt, 0);
          continue;
        }
        throw ApiTimeoutException('request to $path timed out');
      } on http.ClientException catch (e) {
        if (_canRetryTransport(method, attempt)) {
          await _backoff(++attempt, 0);
          continue;
        }
        throw ApiConnectionException('request to $path failed: ${e.message}');
      }

      if (resp.statusCode < 400) return resp;

      final code = resp.statusCode;
      final retryAfter = _retryAfter(resp);
      if (_retryable.contains(code) && attempt < maxRetries) {
        await resp.stream.drain<void>();
        await _backoff(++attempt, retryAfter);
        continue;
      }

      final bodyStr = await resp.stream.bytesToString();
      throw AirforceException.fromResponse(code, bodyStr, resp.headers['x-request-id'], retryAfter);
    }
  }

  // A transport error leaves a POST's outcome unknown — retrying could double-charge a
  // billable request. Only retry idempotent methods.
  bool _canRetryTransport(String method, int attempt) =>
      attempt < maxRetries && method.toUpperCase() != 'POST';

  double _retryAfter(http.StreamedResponse resp) =>
      double.tryParse(resp.headers['retry-after'] ?? '') ?? 0;

  Future<void> _backoff(int attempt, double retryAfter) {
    final base = retryAfter > 0 ? retryAfter : min(pow(2, attempt - 1).toDouble(), 8);
    final jitter = base * 0.25 * Random().nextDouble();
    return Future<void>.delayed(Duration(milliseconds: ((base + jitter) * 1000).round()));
  }

  // --- entry points --------------------------------------------------------

  Future<dynamic> requestJson(
    String method,
    String path, {
    String auth = 'api_key',
    Map<String, String>? query,
    Object? body,
    List<int>? rawBody,
    String? contentType,
    Map<String, String>? headers,
  }) async {
    final bytes = rawBody ?? (body != null ? utf8.encode(jsonEncode(body)) : null);
    final ct = contentType ?? (body != null ? 'application/json' : null);
    final resp = await _send(method, path,
        auth: auth, query: query, body: bytes, contentType: ct, extraHeaders: headers);
    final out = await resp.stream.toBytes();
    return out.isEmpty ? null : jsonDecode(utf8.decode(out));
  }

  Future<List<int>> requestBytes(String method, String path,
      {String auth = 'api_key', Object? body, List<int>? rawBody, String? contentType}) async {
    final bytes = rawBody ?? (body != null ? utf8.encode(jsonEncode(body)) : null);
    final ct = contentType ?? (body != null ? 'application/json' : null);
    final resp = await _send(method, path, auth: auth, body: bytes, contentType: ct);
    return resp.stream.toBytes();
  }

  Stream<dynamic> streamJson(String method, String path, {String auth = 'api_key', Object? body}) async* {
    final bytes = body != null ? utf8.encode(jsonEncode(body)) : null;
    final ct = body != null ? 'application/json' : null;
    final resp = await _send(method, path, auth: auth, body: bytes, contentType: ct, stream: true);
    yield* parseSse(resp.stream);
  }

  Future<(dynamic, String?)> requestJsonCookie(String path, Object? body, Map<String, String>? headers) async {
    final bytes = body != null ? utf8.encode(jsonEncode(body)) : null;
    final ct = body != null ? 'application/json' : null;
    final resp = await _send('POST', path, auth: 'none', body: bytes, contentType: ct, extraHeaders: headers);
    String? cookie;
    final setCookie = resp.headers['set-cookie'];
    if (setCookie != null) {
      cookie = RegExp(r'airforce_session=([^;]+)').firstMatch(setCookie)?.group(1);
    }
    final out = await resp.stream.toBytes();
    final json = out.isEmpty ? null : jsonDecode(utf8.decode(out));
    return (json, cookie);
  }

  // --- convenience ---------------------------------------------------------

  Future<dynamic> get(String path, String auth, {Map<String, String>? query}) =>
      requestJson('GET', path, auth: auth, query: query);
  Future<dynamic> post(String path, String auth, [Object? body]) =>
      requestJson('POST', path, auth: auth, body: body);
  Future<dynamic> method(String m, String path, String auth, [Object? body]) =>
      requestJson(m, path, auth: auth, body: body);
  Future<dynamic> delete(String path, String auth) => requestJson('DELETE', path, auth: auth);
  Future<List<int>> postBytes(String path, String auth, Object? body) =>
      requestBytes('POST', path, auth: auth, body: body);
  Future<List<int>> getBytes(String path, String auth) => requestBytes('GET', path, auth: auth);
  Stream<dynamic> postStream(String path, String auth, Object? body) =>
      streamJson('POST', path, auth: auth, body: body);
  Future<dynamic> multipartJson(String path, List<int> body, String contentType) =>
      requestJson('POST', path, auth: 'api_key', rawBody: body, contentType: contentType);
  Future<List<int>> multipartBytes(String path, List<int> body, String contentType) =>
      requestBytes('POST', path, auth: 'api_key', rawBody: body, contentType: contentType);
  Future<dynamic> form(String path, String encoded) => requestJson('POST', path,
      auth: 'none', rawBody: utf8.encode(encoded), contentType: 'application/x-www-form-urlencoded');
  Future<dynamic> getWithHeader(String path, Map<String, String> headers) =>
      requestJson('GET', path, auth: 'none', headers: headers);
}
