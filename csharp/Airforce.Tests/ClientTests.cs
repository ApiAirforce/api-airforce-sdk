using System.Net;
using System.Text;
using Airforce;
using Xunit;

namespace Airforce.Tests;

internal sealed class MockHandler : HttpMessageHandler
{
    private readonly Queue<Func<HttpResponseMessage>> _responses;
    public readonly List<HttpRequestMessage> Requests = new();

    public MockHandler(params Func<HttpResponseMessage>[] responses) => _responses = new(responses);

    protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken ct)
    {
        Requests.Add(request);
        return Task.FromResult(_responses.Dequeue()());
    }

    public HttpRequestMessage Last => Requests[^1];
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
