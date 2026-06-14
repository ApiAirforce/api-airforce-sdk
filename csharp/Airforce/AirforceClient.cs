namespace Airforce;

/// <summary>
/// The api.airforce API client.
/// <code>
/// using var client = new AirforceClient("sk-air-...");
/// var res = await client.Chat.CreateAsync(new {
///     model = "claude-opus-4.8",
///     messages = new[] { new { role = "user", content = "Hello!" } },
/// });
/// </code>
/// </summary>
public sealed class AirforceClient : IDisposable
{
    private readonly Transport _transport;
    private readonly HttpClient _http;

    public ChatResource Chat { get; }
    public MessagesResource Messages { get; }
    public ResponsesResource Responses { get; }
    public GeminiResource Gemini { get; }
    public ModelsResource Models { get; }
    public ImagesResource Images { get; }
    public AudioResource Audio { get; }
    public VideoResource Video { get; }
    public VoicesResource Voices { get; }
    public AccountResource Account { get; }
    public KeysResource Keys { get; }
    public BillingResource Billing { get; }
    public TwoFactorResource TwoFactor { get; }
    public AuthResource Auth { get; }
    public OAuthResource OAuth { get; }

    public AirforceClient(ClientOptions? options = null)
    {
        options ??= new ClientOptions();

        var apiKey = options.ApiKey ?? Environment.GetEnvironmentVariable("AIRFORCE_API_KEY");
        var sessionToken = options.SessionToken ?? Environment.GetEnvironmentVariable("AIRFORCE_SESSION_TOKEN");
        var baseUrl = options.BaseUrl
            ?? Environment.GetEnvironmentVariable("AIRFORCE_BASE_URL")
            ?? "https://api.airforce";

        _http = options.HttpMessageHandler != null
            ? new HttpClient(options.HttpMessageHandler)
            : new HttpClient();
        // We manage timeouts per-request via a CancellationToken, so disable the client one.
        _http.Timeout = System.Threading.Timeout.InfiniteTimeSpan;

        _transport = new Transport(_http, apiKey, sessionToken, baseUrl,
            options.Timeout, options.MaxRetries, options.DefaultHeaders);

        Chat = new ChatResource(_transport);
        Messages = new MessagesResource(_transport);
        Responses = new ResponsesResource(_transport);
        Gemini = new GeminiResource(_transport);
        Models = new ModelsResource(_transport);
        Images = new ImagesResource(_transport);
        Audio = new AudioResource(_transport);
        Video = new VideoResource(_transport);
        Voices = new VoicesResource(_transport);
        Account = new AccountResource(_transport);
        Keys = new KeysResource(_transport);
        Billing = new BillingResource(_transport);
        TwoFactor = new TwoFactorResource(_transport);
        Auth = new AuthResource(_transport);
        OAuth = new OAuthResource(_transport);
    }

    /// <summary>Convenience constructor taking just an API key.</summary>
    public AirforceClient(string apiKey) : this(new ClientOptions { ApiKey = apiKey }) { }

    public string BaseUrl => _transport.BaseUrl;

    /// <summary>Set the session token (e.g. a JWT obtained elsewhere).</summary>
    public void SetSessionToken(string? token) => _transport.SetSessionToken(token);

    public void Dispose() => _http.Dispose();
}
