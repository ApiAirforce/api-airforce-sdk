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

  test('embeddings.create posts to /v1/embeddings and parses vectors', () async {
    const body = '{"object":"list","data":[{"object":"embedding","index":0,"embedding":[0.1,0.2]}],'
        '"model":"text-embedding-3-small","usage":{"prompt_tokens":2,"total_tokens":2}}';
    final mock = MockClient((req) => streamed(200, body));
    final res = await client(mock).embeddings.create({
      'model': 'text-embedding-3-small',
      'input': ['hello', 'world'],
    });
    expect(res['data'][0]['embedding'], [0.1, 0.2]);
    expect(res['usage']['total_tokens'], 2);
    expect(mock.requests.last.url.path, '/v1/embeddings');
    expect(mock.requests.last.headers['authorization'], 'Bearer sk-air-test');
  });

  test('org.members unwraps the members array and uses the session token', () async {
    const body = '{"members":[{"user_id":"u1","role":"owner","status":"active","joined_at":0}]}';
    final mock = MockClient((req) => streamed(200, body));
    final c = client(mock)..setSessionToken('jwt-1');
    final members = await c.org.members();
    expect(members, isA<List<dynamic>>());
    expect(members[0]['role'], 'owner');
    expect(mock.requests.last.url.path, '/api/org/members');
    expect(mock.requests.last.headers['authorization'], 'Bearer jwt-1');
  });

  test('notifications.list passes paging query and keeps the unread count', () async {
    const body = '{"items":[{"id":"n1","event_id":"e1","kind":"price_drop","params_json":"{}",'
        '"created_at":"2026-07-01T00:00:00Z"}],"unread":1}';
    final mock = MockClient((req) => streamed(200, body));
    final c = client(mock)..setSessionToken('jwt-1');
    final res = await c.notifications.list(limit: 10, before: '2026-07-01T00:00:00Z');
    expect(res['unread'], 1);
    expect(res['items'][0]['id'], 'n1');
    final url = mock.requests.last.url;
    expect(url.path, '/api/me/notifications');
    expect(url.queryParameters['limit'], '10');
    expect(url.queryParameters['before'], '2026-07-01T00:00:00Z');
  });

  test('account.closeAccount sends DELETE with the re-auth body', () async {
    final mock = MockClient((req) => streamed(200, '{"closed":true}'));
    final c = client(mock)..setSessionToken('jwt-1');
    final res = await c.account.closeAccount(password: 'pw', totpCode: '123456');
    expect(res['closed'], true);
    final req = mock.requests.last as http.Request;
    expect(req.method, 'DELETE');
    expect(req.url.path, '/api/me/account');
    final sent = jsonDecode(req.body) as Map<String, dynamic>;
    expect(sent['password'], 'pw');
    expect(sent['totp_code'], '123456');
    expect(sent.containsKey('forfeit_balance_ack'), isFalse);
  });

  test('threeD.generateAndWait polls until the task completes', () async {
    var polls = 0;
    final mock = MockClient((req) {
      if (req.method == 'POST') {
        return streamed(200,
            '{"task_id":"t3d_1","status":"queued","model":"m3d","created":0,"has_result":false}');
      }
      polls++;
      return polls < 2
          ? streamed(200, '{"task_id":"t3d_1","status":"processing","has_result":false}')
          : streamed(200, '{"task_id":"t3d_1","status":"completed","has_result":true,"format":"glb"}');
    });
    final task = await client(mock).threeD.generateAndWait({
      'model': 'm3d',
      'image_urls': ['https://example.com/toy.png'],
    }, pollInterval: Duration.zero);
    expect(task['status'], 'completed');
    expect(task['format'], 'glb');
    expect(mock.requests.first.url.path, '/v1/3d/generations');
    expect(mock.requests.last.url.path, '/v1/3d/tasks/t3d_1');
  });
}
