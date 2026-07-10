using System.Text.Json.Nodes;

namespace Airforce;

/// <summary>Chat completions — <c>POST /v1/chat/completions</c>.</summary>
public sealed class ChatResource : Resource
{
    internal ChatResource(Transport t) : base(t) { }

    /// <summary>Create a non-streaming chat completion. The request needs <c>model</c> and
    /// <c>messages</c>; optional keys include the airforce <c>models</c> fallback array and
    /// <c>reasoning</c> (<c>{format?: "separate"|"inline", exclude?: bool}</c>) — response-side
    /// shaping, consumed server-side and never forwarded upstream: <c>"separate"</c> moves
    /// reasoning into <c>message.reasoning</c> and strips it from <c>content</c>;
    /// <c>exclude: true</c> drops reasoning from the response entirely; absent or
    /// <c>"inline"</c> keeps <c>&lt;think&gt;…&lt;/think&gt;</c> blocks inline in
    /// <c>content</c>.</summary>
    public Task<JsonNode?> CreateAsync(object request, CancellationToken ct = default)
    {
        var body = ToObject(request);
        body["stream"] = false;
        return Transport.PostAsync("/v1/chat/completions", "api_key", body, ct);
    }

    /// <summary>Create a streaming chat completion. With <c>reasoning: {format: "separate"}</c>
    /// reasoning arrives in <c>delta.reasoning</c> instead of <c>delta.content</c>.</summary>
    public IAsyncEnumerable<JsonNode> CreateStreamAsync(object request, CancellationToken ct = default)
    {
        var body = ToObject(request);
        body["stream"] = true;
        return Transport.PostStreamAsync("/v1/chat/completions", "api_key", body, ct);
    }
}

/// <summary>Anthropic-compatible messages — <c>POST /v1/messages</c>.</summary>
public sealed class MessagesResource : Resource
{
    internal MessagesResource(Transport t) : base(t) { }

    public Task<JsonNode?> CreateAsync(object request, CancellationToken ct = default)
    {
        var body = ToObject(request);
        body["stream"] = false;
        return Transport.PostAsync("/v1/messages", "api_key", body, ct);
    }

    public IAsyncEnumerable<JsonNode> CreateStreamAsync(object request, CancellationToken ct = default)
    {
        var body = ToObject(request);
        body["stream"] = true;
        return Transport.PostStreamAsync("/v1/messages", "api_key", body, ct);
    }

    /// <summary>Estimate a prompt's token count locally (no upstream call).</summary>
    public Task<JsonNode?> CountTokensAsync(object request, CancellationToken ct = default)
        => Transport.PostAsync("/v1/messages/count_tokens", "api_key", request, ct);
}

/// <summary>OpenAI Responses API — <c>POST /v1/responses</c>.</summary>
public sealed class ResponsesResource : Resource
{
    internal ResponsesResource(Transport t) : base(t) { }

    public Task<JsonNode?> CreateAsync(object request, CancellationToken ct = default)
    {
        var body = ToObject(request);
        body["stream"] = false;
        return Transport.PostAsync("/v1/responses", "api_key", body, ct);
    }

    public IAsyncEnumerable<JsonNode> CreateStreamAsync(object request, CancellationToken ct = default)
    {
        var body = ToObject(request);
        body["stream"] = true;
        return Transport.PostStreamAsync("/v1/responses", "api_key", body, ct);
    }
}

/// <summary>OpenAI-compatible embeddings — <c>POST /v1/embeddings</c>.</summary>
public sealed class EmbeddingsResource : Resource
{
    internal EmbeddingsResource(Transport t) : base(t) { }

    /// <summary>Create embeddings. The request needs <c>model</c> and a non-empty
    /// <c>input</c> (string, string[], int[], or int[][]); optional keys are
    /// <c>encoding_format</c>, <c>dimensions</c>, and <c>user</c>. Billed on input tokens
    /// only; no streaming. The response is the upstream OpenAI shape verbatim.</summary>
    public Task<JsonNode?> CreateAsync(object request, CancellationToken ct = default)
        => Transport.PostAsync("/v1/embeddings", "api_key", request, ct);
}

/// <summary>Google Gemini-compatible generation — <c>POST /v1beta/models/{model}:{method}</c>.</summary>
public sealed class GeminiResource : Resource
{
    internal GeminiResource(Transport t) : base(t) { }

    public Task<JsonNode?> GenerateContentAsync(string model, object request, CancellationToken ct = default)
        => Transport.PostAsync($"/v1beta/models/{Enc(model)}:generateContent", "api_key", request, ct);

    public IAsyncEnumerable<JsonNode> StreamGenerateContentAsync(string model, object request, CancellationToken ct = default)
        => Transport.PostStreamAsync($"/v1beta/models/{Enc(model)}:streamGenerateContent", "api_key", request, ct);
}
