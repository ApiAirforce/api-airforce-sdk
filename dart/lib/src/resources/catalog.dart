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

  Future<dynamic> detail(String model) =>
      _t.get('/api/models/${Uri.encodeComponent(model)}/detail', 'none');

  Future<dynamic> allowedParams(String model) =>
      _t.get('/api/models/${Uri.encodeComponent(model)}/allowed-params', 'none');

  Future<dynamic> classes() => _t.get('/v1/playground/model-classes', 'none');
}
