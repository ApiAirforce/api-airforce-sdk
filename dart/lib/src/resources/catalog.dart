import '../transport.dart';

/// Model catalog / discovery.
class Models {
  final Transport _t;
  Models(this._t);

  /// List public models (returns the `data` array).
  Future<dynamic> list({bool channels = false}) async {
    final res = await _t.get('/v1/models', 'none', query: channels ? {'channels': '1'} : null);
    return res is Map && res.containsKey('data') ? res['data'] : res;
  }

  /// One model, the same entry [list] returns for it (`GET /v1/models/{model}`).
  /// Ids with slashes such as `BAAI/bge-reranker-v2-m3` are sent as written, not
  /// encoded. An unknown id throws the API's 404 error.
  Future<dynamic> retrieve(String model) => _t.get('/v1/models/$model', 'none');

  Future<dynamic> detail(String model) =>
      _t.get('/api/models/${Uri.encodeComponent(model)}/detail', 'none');

  Future<dynamic> allowedParams(String model) =>
      _t.get('/api/models/${Uri.encodeComponent(model)}/allowed-params', 'none');

  Future<dynamic> classes() => _t.get('/v1/playground/model-classes', 'none');
}
