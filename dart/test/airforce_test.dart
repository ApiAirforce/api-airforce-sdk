import 'dart:convert';

import 'package:airforce/airforce.dart';
import 'package:http/http.dart' as http;
import 'package:test/test.dart';

const completion =
    '{"id":"cmpl_1","object":"chat.completion","created":0,"model":"claude-opus-4.8",'
    '"choices":[{"index":0,"message":{"role":"assistant","content":"hi"},"finish_reason":"stop"}]}';

class MockClient extends http.BaseClient {
  final http.StreamedResponse Function(http.BaseRequest) handler;
  final List<http.BaseRequest> requests = [];
  MockClient(this.handler);

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    requests.add(request);
    return handler(request);
  }
}

http.StreamedResponse streamed(int status, String body, {Map<String, String>? headers}) =>
    http.StreamedResponse(
      Stream.value(utf8.encode(body)),
      status,
      headers: {'content-type': 'application/json', ...?headers},
    );

AirforceClient client(MockClient mock, {String? apiKey = 'sk-air-test'}) =>
    AirforceClient(apiKey: apiKey, baseUrl: 'https://api.airforce', httpClient: mock);

void main() {
  test('chat.create sends Bearer and parses response', () async {
    final mock = MockClient((req) => streamed(200, completion));
    final res = await client(mock).chat.create({
      'model': 'claude-opus-4.8',
      'messages': [
        {'role': 'user', 'content': 'hello'}
      ],
    });
    expect(res['choices'][0]['message']['content'], 'hi');
    expect(mock.requests.last.headers['authorization'], 'Bearer sk-air-test');
    expect(mock.requests.last.url.path, '/v1/chat/completions');
  });

  test('missing api key throws', () {
    final mock = MockClient((req) => streamed(200, '{}'));
    expect(
      () => client(mock, apiKey: null).chat.create({'model': 'm', 'messages': []}),
      throwsA(isA<MissingCredentialException>()),
    );
  });

  test('session endpoint requires a session token', () {
    final mock = MockClient((req) => streamed(200, '{}'));
    expect(() => client(mock).account.me(), throwsA(isA<MissingCredentialException>()));
  });

  test('public endpoint has no auth', () async {
    final mock = MockClient((req) => streamed(200, '{"object":"list","data":[]}'));
    await client(mock).models.list();
    expect(mock.requests.last.headers['authorization'], isNull);
  });

  test('retries on 429 then succeeds', () async {
    var calls = 0;
    final mock = MockClient((req) {
      calls++;
      return calls == 1
          ? streamed(429, '{"error":"slow"}', headers: {'retry-after': '0'})
          : streamed(200, completion);
    });
    final res = await client(mock).chat.create({'model': 'm', 'messages': []});
    expect(res['id'], 'cmpl_1');
    expect(calls, 2);
  });

  test('error mapping for 402', () {
    final mock = MockClient(
        (req) => streamed(402, '{"error":{"message":"no balance","code":"insufficient_balance"}}'));
    expect(
      () => client(mock).chat.create({'model': 'm', 'messages': []}),
      throwsA(isA<AirforceException>()
          .having((e) => e.status, 'status', 402)
          .having((e) => e.isInsufficientBalance, 'isInsufficientBalance', true)
          .having((e) => e.code, 'code', 'insufficient_balance')),
    );
  });

  test('streaming assembles content', () async {
    const sse = 'data: {"choices":[{"index":0,"delta":{"content":"he"},"finish_reason":null}]}\n\n'
        'data: {"choices":[{"index":0,"delta":{"content":"llo"},"finish_reason":"stop"}]}\n\n'
        'data: [DONE]\n\n';
    final mock = MockClient((req) => streamed(200, sse, headers: {'content-type': 'text/event-stream'}));

    final text = StringBuffer();
    await for (final chunk in client(mock).chat.createStream({'model': 'm', 'messages': []})) {
      final c = chunk['choices'][0]['delta']['content'];
      if (c != null) text.write(c);
    }
    expect(text.toString(), 'hello');
  });
}
