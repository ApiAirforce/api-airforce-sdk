import 'dart:convert';

/// Parse a Server-Sent Events byte stream into a stream of decoded JSON values.
/// Iteration stops at the `[DONE]` sentinel.
Stream<dynamic> parseSse(Stream<List<int>> byteStream) async* {
  final lines = byteStream.transform(utf8.decoder).transform(const LineSplitter());
  final data = <String>[];

  await for (final line in lines) {
    if (line.isEmpty) {
      if (data.isEmpty) continue;
      final payload = data.join('\n');
      data.clear();
      if (payload == '[DONE]') return;
      yield jsonDecode(payload);
    } else if (line.startsWith(':')) {
      // comment / keep-alive
    } else if (line.startsWith('data:')) {
      var value = line.substring(5);
      if (value.startsWith(' ')) value = value.substring(1);
      data.add(value);
    }
  }

  if (data.isNotEmpty) {
    final payload = data.join('\n');
    if (payload != '[DONE]') yield jsonDecode(payload);
  }
}
