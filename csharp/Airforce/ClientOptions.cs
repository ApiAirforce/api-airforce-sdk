namespace Airforce;

/// <summary>Configuration for <see cref="AirforceClient"/>.</summary>
public sealed class ClientOptions
{
    /// <summary>API key (sk-air-…). Falls back to the AIRFORCE_API_KEY env var.</summary>
    public string? ApiKey { get; set; }

    /// <summary>Session JWT for account/billing endpoints. Falls back to AIRFORCE_SESSION_TOKEN.</summary>
    public string? SessionToken { get; set; }

    /// <summary>Base URL. Default: https://api.airforce (or AIRFORCE_BASE_URL).</summary>
    public string? BaseUrl { get; set; }

    /// <summary>Per-request timeout. Default 60s.</summary>
    public TimeSpan Timeout { get; set; } = TimeSpan.FromSeconds(60);

    /// <summary>Automatic retries on 429/5xx/network errors. Default 2.</summary>
    public int MaxRetries { get; set; } = 2;

    /// <summary>Headers added to every request.</summary>
    public IDictionary<string, string> DefaultHeaders { get; } = new Dictionary<string, string>();

    /// <summary>Optional custom message handler (e.g. for testing).</summary>
    public HttpMessageHandler? HttpMessageHandler { get; set; }
}
