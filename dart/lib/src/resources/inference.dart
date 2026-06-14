import '../transport.dart';

/// Chat completions — `POST /v1/chat/completions`.
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

/// Google Gemini-compatible generation — `POST /v1beta/models/{model}:{method}`.
class Gemini {
  final Transport _t;
  Gemini(this._t);

  Future<dynamic> generateContent(String model, Map<String, dynamic> request) =>
      _t.post('/v1beta/models/${Uri.encodeComponent(model)}:generateContent', 'api_key', request);

  Stream<dynamic> streamGenerateContent(String model, Map<String, dynamic> request) =>
      _t.postStream('/v1beta/models/${Uri.encodeComponent(model)}:streamGenerateContent', 'api_key', request);
}
