import '../transport.dart';

/// Chat completions — `POST /v1/chat/completions`.
///
/// Request maps are passed through verbatim, so every documented parameter —
/// including the airforce extensions (`models` fallback, `skill`/`skills`,
/// `transforms`) — works as-is.
///
/// The optional `reasoning` parameter (`{'format': 'separate'|'inline',
/// 'exclude': bool}`) shapes how reasoning appears in the response. It is
/// consumed server-side and never forwarded upstream: `'separate'` moves
/// reasoning into `message.reasoning` / `delta.reasoning` and strips it from
/// `content`; `'exclude': true` drops reasoning from the response entirely;
/// absent or `'inline'` keeps reasoning wrapped in `<think>…</think>` inside
/// `content`.
class Chat {
  final Transport _t;
  Chat(this._t);

  Future<dynamic> create(Map<String, dynamic> request) =>
      _t.post('/v1/chat/completions', 'api_key', {...request, 'stream': false});

  Stream<dynamic> createStream(Map<String, dynamic> request) =>
      _t.postStream('/v1/chat/completions', 'api_key', {...request, 'stream': true});
}

/// Anthropic-compatible messages — `POST /v1/messages`.
class Messages {
  final Transport _t;
  Messages(this._t);

  Future<dynamic> create(Map<String, dynamic> request) =>
      _t.post('/v1/messages', 'api_key', {...request, 'stream': false});

  Stream<dynamic> createStream(Map<String, dynamic> request) =>
      _t.postStream('/v1/messages', 'api_key', {...request, 'stream': true});

  Future<dynamic> countTokens(Map<String, dynamic> request) =>
      _t.post('/v1/messages/count_tokens', 'api_key', request);
}

/// OpenAI Responses API — `POST /v1/responses`.
class Responses {
  final Transport _t;
  Responses(this._t);

  Future<dynamic> create(Map<String, dynamic> request) =>
      _t.post('/v1/responses', 'api_key', {...request, 'stream': false});

  Stream<dynamic> createStream(Map<String, dynamic> request) =>
      _t.postStream('/v1/responses', 'api_key', {...request, 'stream': true});
}

/// Embeddings — `POST /v1/embeddings`.
///
/// OpenAI-compatible embeddings with smart routing + provider fallback.
/// Billed on input tokens only; no streaming.
class Embeddings {
  final Transport _t;
  Embeddings(this._t);

  /// `{model, input: string | string[] | int[] | int[][], encoding_format?,
  /// dimensions?, user?}` → the upstream OpenAI shape
  /// (`{object: 'list', data: [{embedding, index}], model, usage}`).
  Future<dynamic> create(Map<String, dynamic> request) =>
      _t.post('/v1/embeddings', 'api_key', request);
}

/// Google Gemini-compatible generation — `POST /v1beta/models/{model}:{method}`.
class Gemini {
  final Transport _t;
  Gemini(this._t);

  Future<dynamic> generateContent(String model, Map<String, dynamic> request) =>
      _t.post('/v1beta/models/${Uri.encodeComponent(model)}:generateContent', 'api_key', request);

  Stream<dynamic> streamGenerateContent(String model, Map<String, dynamic> request) =>
      _t.postStream('/v1beta/models/${Uri.encodeComponent(model)}:streamGenerateContent', 'api_key', request);
}
