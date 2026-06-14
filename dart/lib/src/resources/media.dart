import '../exceptions.dart';
import '../transport.dart';

String _enc(String s) => Uri.encodeComponent(s);

/// Image generation — `POST /v1/images/generations`.
class Images {
  final Transport _t;
  Images(this._t);

  Future<dynamic> generate(Map<String, dynamic> request) =>
      _t.post('/v1/images/generations', 'api_key', request);
}

/// Audio — TTS, music, SFX, transcription, dubbing, voices (`/v1/audio/*`).
class Audio {
  final Transport _t;
  Audio(this._t);

  Future<List<int>> speech(Map<String, dynamic> request) =>
      _t.postBytes('/v1/audio/speech', 'api_key', request);

  Future<List<int>> music(Map<String, dynamic> request) =>
      _t.postBytes('/v1/audio/music', 'api_key', request);

  Future<List<int>> soundEffects(Map<String, dynamic> request) =>
      _t.postBytes('/v1/audio/sound-effects', 'api_key', request);

  Future<dynamic> transcriptions(String model, List<int> file, String filename,
      {Map<String, String>? extra}) {
    final m = buildMultipart(_fields(model, extra), [(field: 'file', filename: filename, data: file)]);
    return _t.multipartJson('/v1/audio/transcriptions', m.body, m.contentType);
  }

  Future<List<int>> audioIsolation(String model, List<int> file, String filename, {String? output}) {
    final fields = {'model': model, if (output != null) 'output': output};
    final m = buildMultipart(fields, [(field: 'file', filename: filename, data: file)]);
    return _t.multipartBytes('/v1/audio/audio-isolation', m.body, m.contentType);
  }

  Future<List<int>> voiceChanger(String model, List<int> file, String filename, String voice) {
    final m = buildMultipart({'model': model, 'voice': voice}, [(field: 'file', filename: filename, data: file)]);
    return _t.multipartBytes('/v1/audio/voice-changer', m.body, m.contentType);
  }

  Future<dynamic> dubbing(String model, List<int> file, String filename, String targetLang,
      {Map<String, String>? extra}) {
    final fields = _fields(model, extra)..['target_lang'] = targetLang;
    final m = buildMultipart(fields, [(field: 'file', filename: filename, data: file)]);
    return _t.multipartJson('/v1/audio/dubbing', m.body, m.contentType);
  }

  Future<dynamic> dubbingStatus(String id) => _t.get('/v1/audio/dubbing/${_enc(id)}', 'api_key');

  Future<List<int>> dubbingAudio(String id, String lang) =>
      _t.getBytes('/v1/audio/dubbing/${_enc(id)}/audio/${_enc(lang)}', 'api_key');

  Future<dynamic> voices() async {
    final res = await _t.get('/v1/audio/voices', 'api_key');
    return res is Map && res.containsKey('voices') ? res['voices'] : res;
  }

  Map<String, String> _fields(String model, Map<String, String>? extra) =>
      {'model': model, ...?extra};
}

/// Async video generation — `/v1/video/*`.
class Video {
  static const _terminal = {'completed', 'failed', 'expired'};
  final Transport _t;
  Video(this._t);

  Future<dynamic> generate(Map<String, dynamic> request) =>
      _t.post('/v1/video/generations', 'api_key', request);

  Future<dynamic> getTask(String id) => _t.get('/v1/video/tasks/${_enc(id)}', 'api_key');

  Future<dynamic> listTasks() async {
    final res = await _t.get('/v1/video/tasks', 'api_key');
    return res is Map && res.containsKey('data') ? res['data'] : res;
  }

  Future<dynamic> deleteTask(String id) => _t.delete('/v1/video/tasks/${_enc(id)}', 'api_key');

  /// Poll a task until it reaches a terminal state.
  Future<dynamic> waitForCompletion(String id,
      {Duration pollInterval = const Duration(milliseconds: 2500),
      Duration timeout = const Duration(minutes: 10)}) async {
    final deadline = DateTime.now().add(timeout);
    while (true) {
      final task = await getTask(id);
      final status = task is Map ? task['status'] as String? ?? '' : '';
      if (status == 'completed') return task;
      if (_terminal.contains(status)) {
        throw AirforceException('video task $id ended with status $status', code: status);
      }
      if (DateTime.now().isAfter(deadline)) {
        throw AirforceException('timed out waiting for video task $id', code: 'wait_timeout');
      }
      await Future<void>.delayed(pollInterval);
    }
  }

  Future<dynamic> generateAndWait(Map<String, dynamic> request,
      {Duration pollInterval = const Duration(milliseconds: 2500),
      Duration timeout = const Duration(minutes: 10)}) async {
    final task = await generate(request);
    final id = task is Map ? task['task_id'] as String? : null;
    if (id == null) throw AirforceException('video task response had no task_id');
    return waitForCompletion(id, pollInterval: pollInterval, timeout: timeout);
  }
}

/// Voice cloning — `/v1/voices/*`.
class Voices {
  final Transport _t;
  Voices(this._t);

  Future<dynamic> consentText() => _t.get('/v1/voices/consent-text', 'none');

  /// Create a cloned voice from one or more samples (filename + bytes).
  Future<dynamic> clone(String name, String consentHash, List<({String filename, List<int> data})> samples,
      {Map<String, String>? extra}) {
    final fields = {'name': name, 'consent_hash': consentHash, ...?extra};
    final files = [for (final s in samples) (field: 'files', filename: s.filename, data: s.data)];
    final m = buildMultipart(fields, files);
    return _t.multipartJson('/v1/voices/clone', m.body, m.contentType);
  }

  Future<dynamic> library() async {
    final res = await _t.get('/v1/voices/library', 'api_key');
    return res is Map && res.containsKey('voices') ? res['voices'] : res;
  }

  Future<dynamic> update(String voiceId, Map<String, dynamic> body) =>
      _t.method('PATCH', '/v1/voices/clone/${_enc(voiceId)}', 'api_key', body);

  Future<dynamic> delete(String voiceId) => _t.delete('/v1/voices/clone/${_enc(voiceId)}', 'api_key');
}
