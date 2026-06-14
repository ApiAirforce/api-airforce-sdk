using System.Net;
using System.Net.Http.Headers;
using System.Runtime.CompilerServices;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Text.RegularExpressions;

namespace Airforce;

internal sealed class RequestOptions
{
    public string Auth = "api_key";
    public IDictionary<string, string?>? Query;
    public byte[]? Body;
    public string? ContentType;
    public IDictionary<string, string>? Headers;
}

internal sealed class Transport
{
    internal const string Version = "0.0.1";
    private static readonly HashSet<int> Retryable = new() { 408, 429, 500, 502, 503, 504 };
    private static readonly Random Rng = new();

    private readonly HttpClient _http;
    private readonly string _baseUrl;
    private readonly TimeSpan _timeout;
    private readonly int _maxRetries;
    private readonly IDictionary<string, string> _defaultHeaders;

    private string? _apiKey;
    private string? _sessionToken;

    public Transport(HttpClient http, string? apiKey, string? sessionToken, string baseUrl,
        TimeSpan timeout, int maxRetries, IDictionary<string, string> defaultHeaders)
    {
        _http = http;
        _apiKey = apiKey;
        _sessionToken = sessionToken;
        _baseUrl = baseUrl.TrimEnd('/');
        _timeout = timeout;
        _maxRetries = maxRetries;
        _defaultHeaders = defaultHeaders;
    }

    public string BaseUrl => _baseUrl;
    public void SetSessionToken(string? token) => _sessionToken = token;

    // --- public entry points -------------------------------------------------

    public async Task<JsonNode?> RequestJsonAsync(HttpMethod method, string path, RequestOptions o, CancellationToken ct)
    {
        using var resp = await SendAsync(method, path, o, HttpCompletionOption.ResponseContentRead, ct).ConfigureAwait(false);
        if (resp.StatusCode == HttpStatusCode.NoContent) return null;
        var bytes = await resp.Content.ReadAsByteArrayAsync(ct).ConfigureAwait(false);
        return bytes.Length == 0 ? null : JsonNode.Parse(bytes);
    }

    public async Task<byte[]> RequestBytesAsync(HttpMethod method, string path, RequestOptions o, CancellationToken ct)
    {
        using var resp = await SendAsync(method, path, o, HttpCompletionOption.ResponseContentRead, ct).ConfigureAwait(false);
        return await resp.Content.ReadAsByteArrayAsync(ct).ConfigureAwait(false);
    }

    public async IAsyncEnumerable<JsonNode> StreamAsync(HttpMethod method, string path, RequestOptions o,
        [EnumeratorCancellation] CancellationToken ct = default)
    {
        var resp = await SendAsync(method, path, o, HttpCompletionOption.ResponseHeadersRead, ct).ConfigureAwait(false);
        try
        {
            var stream = await resp.Content.ReadAsStreamAsync(ct).ConfigureAwait(false);
            await foreach (var node in SseStream.ParseAsync(stream, ct).ConfigureAwait(false))
                yield return node;
        }
        finally
        {
            resp.Dispose();
        }
    }

    public async Task<(JsonNode? Json, string? Cookie)> RequestJsonWithCookieAsync(
        HttpMethod method, string path, RequestOptions o, CancellationToken ct)
    {
        using var resp = await SendAsync(method, path, o, HttpCompletionOption.ResponseContentRead, ct).ConfigureAwait(false);
        var bytes = await resp.Content.ReadAsByteArrayAsync(ct).ConfigureAwait(false);
        JsonNode? json = bytes.Length == 0 ? null : JsonNode.Parse(bytes);
        string? cookie = null;
        if (resp.Headers.TryGetValues("Set-Cookie", out var cookies))
        {
            foreach (var c in cookies)
            {
                var m = Regex.Match(c, "airforce_session=([^;]+)");
                if (m.Success) { cookie = Uri.UnescapeDataString(m.Groups[1].Value); break; }
            }
        }
        return (json, cookie);
    }

    // --- convenience wrappers ------------------------------------------------

    public Task<JsonNode?> PostAsync(string path, string auth, object? body, CancellationToken ct = default)
        => RequestJsonAsync(HttpMethod.Post, path, JsonOptions(auth, body), ct);

    public Task<JsonNode?> MethodAsync(HttpMethod method, string path, string auth, object? body, CancellationToken ct = default)
        => RequestJsonAsync(method, path, JsonOptions(auth, body), ct);

    public Task<JsonNode?> GetAsync(string path, string auth, IDictionary<string, string?>? query = null, CancellationToken ct = default)
        => RequestJsonAsync(HttpMethod.Get, path, new RequestOptions { Auth = auth, Query = query }, ct);

    public Task<JsonNode?> DeleteAsync(string path, string auth, CancellationToken ct = default)
        => RequestJsonAsync(HttpMethod.Delete, path, new RequestOptions { Auth = auth }, ct);

    public Task<byte[]> PostBytesAsync(string path, string auth, object? body, CancellationToken ct = default)
        => RequestBytesAsync(HttpMethod.Post, path, JsonOptions(auth, body), ct);

    public Task<byte[]> GetBytesAsync(string path, string auth, CancellationToken ct = default)
        => RequestBytesAsync(HttpMethod.Get, path, new RequestOptions { Auth = auth }, ct);

    public IAsyncEnumerable<JsonNode> PostStreamAsync(string path, string auth, object? body, CancellationToken ct = default)
        => StreamAsync(HttpMethod.Post, path, JsonOptions(auth, body), ct);

    public Task<JsonNode?> RawAsync(HttpMethod method, string path, RequestOptions o, CancellationToken ct = default)
        => RequestJsonAsync(method, path, o, ct);

    public static RequestOptions JsonOptions(string auth, object? body)
    {
        var o = new RequestOptions { Auth = auth };
        if (body != null)
        {
            o.Body = JsonSerializer.SerializeToUtf8Bytes(body);
            o.ContentType = "application/json";
        }
        return o;
    }

    // --- internals -----------------------------------------------------------

    private string? ResolveToken(string auth)
    {
        if (auth == "none") return null;
        // Session endpoints require a session JWT — never substitute an API key.
        var token = auth == "session" ? _sessionToken : (_apiKey ?? _sessionToken);
        if (token == null)
            throw new MissingCredentialException(auth == "session"
                ? "This endpoint requires a session token (set SessionToken / Auth.LoginAsync)."
                : "This endpoint requires an API key (set ApiKey).");
        return token;
    }

    private string BuildUrl(string path, IDictionary<string, string?>? query)
    {
        var url = _baseUrl + (path.StartsWith('/') ? path : "/" + path);
        if (query == null || query.Count == 0) return url;
        var qs = new List<string>();
        foreach (var kv in query)
            if (kv.Value != null)
                qs.Add($"{Uri.EscapeDataString(kv.Key)}={Uri.EscapeDataString(kv.Value)}");
        return qs.Count == 0 ? url : url + "?" + string.Join("&", qs);
    }

    private HttpRequestMessage BuildRequest(HttpMethod method, string url, RequestOptions o, string? token, bool stream)
    {
        var req = new HttpRequestMessage(method, url);
        if (o.Body != null)
        {
            var content = new ByteArrayContent(o.Body);
            if (o.ContentType != null)
                content.Headers.ContentType = MediaTypeHeaderValue.Parse(o.ContentType);
            req.Content = content;
        }
        req.Headers.TryAddWithoutValidation("user-agent", $"airforce-sdk-dotnet/{Version}");
        req.Headers.TryAddWithoutValidation("x-airforce-sdk", $"dotnet/{Version}");
        req.Headers.TryAddWithoutValidation("accept", stream ? "text/event-stream" : "application/json");
        if (token != null)
            req.Headers.TryAddWithoutValidation("authorization", $"Bearer {token}");
        foreach (var kv in _defaultHeaders) req.Headers.TryAddWithoutValidation(kv.Key, kv.Value);
        if (o.Headers != null)
            foreach (var kv in o.Headers) req.Headers.TryAddWithoutValidation(kv.Key, kv.Value);
        return req;
    }

    private async Task<HttpResponseMessage> SendAsync(
        HttpMethod method, string path, RequestOptions o, HttpCompletionOption completion, CancellationToken ct)
    {
        var url = BuildUrl(path, o.Query);
        var token = ResolveToken(o.Auth);
        var streaming = completion == HttpCompletionOption.ResponseHeadersRead;

        for (var attempt = 0; ; attempt++)
        {
            using var timeoutCts = new CancellationTokenSource(_timeout);
            using var linked = CancellationTokenSource.CreateLinkedTokenSource(ct, timeoutCts.Token);
            using var req = BuildRequest(method, url, o, token, streaming);

            HttpResponseMessage resp;
            try
            {
                resp = await _http.SendAsync(req, completion, linked.Token).ConfigureAwait(false);
            }
            catch (OperationCanceledException) when (timeoutCts.IsCancellationRequested && !ct.IsCancellationRequested)
            {
                if (CanRetryTransport(method, attempt)) { await Backoff(attempt + 1, 0, ct).ConfigureAwait(false); continue; }
                throw new ApiTimeoutException($"airforce: request to {path} timed out");
            }
            catch (HttpRequestException ex)
            {
                if (CanRetryTransport(method, attempt)) { await Backoff(attempt + 1, 0, ct).ConfigureAwait(false); continue; }
                throw new ApiConnectionException($"airforce: request to {path} failed: {ex.Message}", ex);
            }

            if ((int)resp.StatusCode < 400) return resp;

            if (Retryable.Contains((int)resp.StatusCode) && attempt < _maxRetries)
            {
                var ra = RetryAfterSeconds(resp);
                resp.Dispose();
                await Backoff(attempt + 1, ra, ct).ConfigureAwait(false);
                continue;
            }

            var status = (int)resp.StatusCode;
            var body = await resp.Content.ReadAsStringAsync(ct).ConfigureAwait(false);
            var reqId = resp.Headers.TryGetValues("x-request-id", out var ids) ? ids.FirstOrDefault() : null;
            var retryAfter = RetryAfterSeconds(resp);
            resp.Dispose();
            throw AirforceException.FromResponse(status, body, reqId, retryAfter);
        }
    }

    // A transport error leaves a POST's outcome unknown — retrying could double-charge
    // a billable request. Only retry idempotent methods on transport/timeout failures.
    private bool CanRetryTransport(HttpMethod method, int attempt) =>
        attempt < _maxRetries && method != HttpMethod.Post;

    private static double RetryAfterSeconds(HttpResponseMessage resp) =>
        resp.Headers.TryGetValues("retry-after", out var values)
            && double.TryParse(values.FirstOrDefault(), out var secs)
            ? secs : 0;

    private async Task Backoff(int attempt, double retryAfter, CancellationToken ct)
    {
        var baseSecs = retryAfter > 0 ? retryAfter : Math.Min(Math.Pow(2, attempt - 1), 8);
        double jitter;
        lock (Rng) jitter = baseSecs * 0.25 * Rng.NextDouble();
        await Task.Delay(TimeSpan.FromSeconds(baseSecs + jitter), ct).ConfigureAwait(false);
    }
}
