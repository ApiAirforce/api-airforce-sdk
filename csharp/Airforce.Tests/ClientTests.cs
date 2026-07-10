using System.Net;
using System.Text;
using Airforce;
using Xunit;

namespace Airforce.Tests;

internal sealed class MockHandler : HttpMessageHandler
{
    private readonly Queue<Func<HttpResponseMessage>> _responses;
    public readonly List<HttpRequestMessage> Requests = new();
    // Bodies are read eagerly — the transport disposes the request (and its content)
    // as soon as the call returns.
    public readonly List<string?> Bodies = new();

    public MockHandler(params Func<HttpResponseMessage>[] responses) => _responses = new(responses);

    protected override async Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken ct)
    {
        Requests.Add(request);
        Bodies.Add(request.Content == null
            ? null
            : await request.Content.ReadAsStringAsync(ct));
        return _responses.Dequeue()();
    }

    public HttpRequestMessage Last => Requests[^1];
    public string? LastBody => Bodies[^1];
    public static string? Auth(HttpRequestMessage r) =>
        r.Headers.TryGetValues("authorization", out var v) ? v.FirstOrDefault() : null;
}

public class ClientTests
{
    private const string Completion =
        "{\"id\":\"cmpl_1\",\"object\":\"chat.completion\",\"created\":0,\"model\":\"claude-opus-4.8\"," +
        "\"choices\":[{\"index\":0,\"message\":{\"role\":\"assistant\",\"content\":\"hi\"},\"finish_reason\":\"stop\"}]}";

    private static Func<HttpResponseMessage> Json(HttpStatusCode status, string body, (string, string)? header = null) =>
        () =>
        {
            var resp = new HttpResponseMessage(status)
            {
                Content = new StringContent(body, Encoding.UTF8, "application/json"),
            };
            if (header is { } h) resp.Headers.TryAddWithoutValidation(h.Item1, h.Item2);
            return resp;
        };

    private static AirforceClient Client(MockHandler handler, string? apiKey = "sk-air-test") =>
        new(new ClientOptions { ApiKey = apiKey, BaseUrl = "https://api.airforce", HttpMessageHandler = handler });

    [Fact]
    public async Task ChatCreate_SendsBearerAndParsesResponse()
    {
        var handler = new MockHandler(Json(HttpStatusCode.OK, Completion));
        using var client = Client(handler);

        var res = await client.Chat.CreateAsync(new
        {
            model = "claude-opus-4.8",
            messages = new[] { new { role = "user", content = "hello" } },
        });

        Assert.Equal("hi", res!["choices"]![0]!["message"]!["content"]!.GetValue<string>());
        Assert.Equal("Bearer sk-air-test", MockHandler.Auth(handler.Last));
        Assert.Equal("/v1/chat/completions", handler.Last.RequestUri!.AbsolutePath);
    }

    [Fact]
    public async Task MissingApiKey_Throws()
    {
        var handler = new MockHandler(Json(HttpStatusCode.OK, "{}"));
        using var client = Client(handler, apiKey: null);
        await Assert.ThrowsAsync<MissingCredentialException>(() =>
            client.Chat.CreateAsync(new { model = "m", messages = Array.Empty<object>() }));
    }

    [Fact]
    public async Task SessionEndpoint_RequiresSessionToken()
    {
        var handler = new MockHandler(Json(HttpStatusCode.OK, "{}"));
        using var client = Client(handler); // api key only
        await Assert.ThrowsAsync<MissingCredentialException>(() => client.Account.MeAsync());
    }

    [Fact]
    public async Task PublicEndpoint_HasNoAuth()
    {
        var handler = new MockHandler(Json(HttpStatusCode.OK, "{\"object\":\"list\",\"data\":[]}"));
        using var client = Client(handler);
        await client.Models.ListAsync();
        Assert.Null(MockHandler.Auth(handler.Last));
    }

    [Fact]
    public async Task RetriesOn429_ThenSucceeds()
    {
        var handler = new MockHandler(
            Json(HttpStatusCode.TooManyRequests, "{\"error\":\"slow\"}", ("retry-after", "0")),
            Json(HttpStatusCode.OK, Completion));
        using var client = Client(handler);

        var res = await client.Chat.CreateAsync(new { model = "m", messages = Array.Empty<object>() });
        Assert.Equal("cmpl_1", res!["id"]!.GetValue<string>());
        Assert.Equal(2, handler.Requests.Count);
    }

    [Fact]
    public async Task ErrorMapping_PaymentRequired()
    {
        var handler = new MockHandler(Json((HttpStatusCode)402,
            "{\"error\":{\"message\":\"no balance\",\"code\":\"insufficient_balance\"}}"));
        using var client = Client(handler);

        var ex = await Assert.ThrowsAsync<AirforceException>(() =>
            client.Chat.CreateAsync(new { model = "m", messages = Array.Empty<object>() }));
        Assert.Equal(402, ex.Status);
        Assert.True(ex.IsInsufficientBalance);
        Assert.Equal("insufficient_balance", ex.Code);
    }

    [Fact]
    public async Task EmbeddingsCreate_SendsBearerAndParsesResponse()
    {
        const string body =
            "{\"object\":\"list\",\"data\":[{\"object\":\"embedding\",\"index\":0,\"embedding\":[0.1,0.2]}]," +
            "\"model\":\"text-embedding-3-small\",\"usage\":{\"prompt_tokens\":2,\"total_tokens\":2}}";
        var handler = new MockHandler(Json(HttpStatusCode.OK, body));
        using var client = Client(handler);

        var res = await client.Embeddings.CreateAsync(new { model = "text-embedding-3-small", input = "hello" });

        Assert.Equal(0.2, res!["data"]![0]!["embedding"]![1]!.GetValue<double>());
        Assert.Equal(2, res["usage"]!["prompt_tokens"]!.GetValue<int>());
        Assert.Equal("Bearer sk-air-test", MockHandler.Auth(handler.Last));
        Assert.Equal(HttpMethod.Post, handler.Last.Method);
        Assert.Equal("/v1/embeddings", handler.Last.RequestUri!.AbsolutePath);
    }

    [Fact]
    public async Task OrgMembers_UsesSessionAndUnwrapsList()
    {
        var handler = new MockHandler(Json(HttpStatusCode.OK,
            "{\"members\":[{\"user_id\":\"u1\",\"role\":\"owner\",\"status\":\"active\"}]}"));
        using var client = Client(handler);
        client.SetSessionToken("jwt-test");

        var members = await client.Org.MembersAsync();

        Assert.Equal("owner", members![0]!["role"]!.GetValue<string>());
        Assert.Equal("Bearer jwt-test", MockHandler.Auth(handler.Last));
        Assert.Equal("/api/org/members", handler.Last.RequestUri!.AbsolutePath);
    }

    [Fact]
    public async Task NotificationsList_SendsCursorQuery()
    {
        var handler = new MockHandler(Json(HttpStatusCode.OK,
            "{\"items\":[{\"id\":\"n1\",\"kind\":\"price_drop\",\"created_at\":\"2026-01-01T00:00:00Z\"}],\"unread\":1}"));
        using var client = Client(handler);
        client.SetSessionToken("jwt-test");

        var res = await client.Notifications.ListAsync(limit: 10, before: "2026-01-02T00:00:00Z");

        Assert.Equal(1, res!["unread"]!.GetValue<int>());
        Assert.Equal("n1", res["items"]![0]!["id"]!.GetValue<string>());
        Assert.Equal("/api/me/notifications", handler.Last.RequestUri!.AbsolutePath);
        Assert.Contains("limit=10", handler.Last.RequestUri!.Query);
        Assert.Contains("before=", handler.Last.RequestUri!.Query);
    }

    [Fact]
    public async Task CloseAccount_SendsDeleteWithReauthBody()
    {
        var handler = new MockHandler(Json(HttpStatusCode.OK, "{\"closed\":true}"));
        using var client = Client(handler);
        client.SetSessionToken("jwt-test");

        var res = await client.Account.CloseAccountAsync("hunter2", totpCode: "123456", forfeitBalanceAck: true);

        Assert.True(res!["closed"]!.GetValue<bool>());
        Assert.Equal(HttpMethod.Delete, handler.Last.Method);
        Assert.Equal("/api/me/account", handler.Last.RequestUri!.AbsolutePath);
        Assert.Contains("\"password\":\"hunter2\"", handler.LastBody);
        Assert.Contains("\"totp_code\":\"123456\"", handler.LastBody);
        Assert.Contains("\"forfeit_balance_ack\":true", handler.LastBody);
    }

    [Fact]
    public async Task ThreeDGenerateAndWait_PollsUntilCompleted()
    {
        var handler = new MockHandler(
            Json(HttpStatusCode.OK, "{\"task_id\":\"t3d_1\",\"status\":\"queued\",\"model\":\"trellis-2\",\"has_result\":false}"),
            Json(HttpStatusCode.OK, "{\"task_id\":\"t3d_1\",\"status\":\"processing\",\"model\":\"trellis-2\",\"has_result\":false}"),
            Json(HttpStatusCode.OK, "{\"task_id\":\"t3d_1\",\"status\":\"completed\",\"model\":\"trellis-2\",\"has_result\":true,\"format\":\"glb\"}"));
        using var client = Client(handler);

        var task = await client.ThreeD.GenerateAndWaitAsync(
            new { model = "trellis-2", image_urls = new[] { "https://example.com/chair.png" } },
            pollInterval: TimeSpan.Zero);

        Assert.Equal("completed", task!["status"]!.GetValue<string>());
        Assert.Equal("glb", task["format"]!.GetValue<string>());
        Assert.Equal(3, handler.Requests.Count);
        Assert.Equal("/v1/3d/generations", handler.Requests[0].RequestUri!.AbsolutePath);
        Assert.Equal("/v1/3d/tasks/t3d_1", handler.Last.RequestUri!.AbsolutePath);
    }

    [Fact]
    public async Task Streaming_AssemblesContent()
    {
        const string sse =
            "data: {\"choices\":[{\"index\":0,\"delta\":{\"content\":\"he\"},\"finish_reason\":null}]}\n\n" +
            "data: {\"choices\":[{\"index\":0,\"delta\":{\"content\":\"llo\"},\"finish_reason\":\"stop\"}]}\n\n" +
            "data: [DONE]\n\n";
        var handler = new MockHandler(() =>
        {
            var resp = new HttpResponseMessage(HttpStatusCode.OK)
            {
                Content = new StringContent(sse, Encoding.UTF8, "text/event-stream"),
            };
            return resp;
        });
        using var client = Client(handler);

        var text = new StringBuilder();
        await foreach (var chunk in client.Chat.CreateStreamAsync(new { model = "m", messages = Array.Empty<object>() }))
        {
            var c = chunk["choices"]?[0]?["delta"]?["content"]?.GetValue<string>();
            if (c != null) text.Append(c);
        }
        Assert.Equal("hello", text.ToString());
    }
}
