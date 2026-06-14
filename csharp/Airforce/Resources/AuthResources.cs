using System.Security.Cryptography;
using System.Text;
using System.Text.Json.Nodes;

namespace Airforce;

/// <summary>Two-factor authentication — <c>/api/2fa/*</c>.</summary>
public sealed class TwoFactorResource : Resource
{
    internal TwoFactorResource(Transport t) : base(t) { }

    public Task<JsonNode?> SetupInitAsync(CancellationToken ct = default)
        => Transport.PostAsync("/api/2fa/setup-init", "session", null, ct);

    public Task<JsonNode?> SetupVerifyAsync(string code, CancellationToken ct = default)
        => Transport.PostAsync("/api/2fa/setup-verify", "session", new { code }, ct);

    public Task<JsonNode?> DisableAsync(string password, string code, CancellationToken ct = default)
        => Transport.PostAsync("/api/2fa/disable", "session", new { password, code }, ct);

    public Task<JsonNode?> RegenerateBackupCodesAsync(string code, CancellationToken ct = default)
        => Transport.PostAsync("/api/2fa/regenerate-backup-codes", "session", new { code }, ct);

    public Task<JsonNode?> VerifyStepUpAsync(string code, CancellationToken ct = default)
        => Transport.PostAsync("/api/2fa/verify-step-up", "session", new { code }, ct);

    public Task<JsonNode?> StepUpStatusAsync(CancellationToken ct = default)
        => Transport.GetAsync("/api/2fa/step-up-status", "session", null, ct);
}

/// <summary>Authentication — <c>/auth/*</c>. Login/signup adopt the session token automatically.</summary>
public sealed class AuthResource : Resource
{
    internal AuthResource(Transport t) : base(t) { }

    private async Task<JsonNode?> SubmitAsync(string path, object body, IDictionary<string, string>? headers, CancellationToken ct)
    {
        var options = Transport.JsonOptions("none", body);
        options.Headers = headers;
        var (json, cookie) = await Transport.RequestJsonWithCookieAsync(HttpMethod.Post, path, options, ct).ConfigureAwait(false);
        if (cookie != null)
        {
            Transport.SetSessionToken(cookie);
            if (json is JsonObject obj) obj["session_token"] = cookie;
        }
        return json;
    }

    public Task<JsonNode?> SignupAsync(object request, CancellationToken ct = default)
        => SubmitAsync("/auth/signup", request, null, ct);

    public Task<JsonNode?> SignupPrecheckAsync(object request, CancellationToken ct = default)
        => Transport.PostAsync("/auth/signup/precheck", "none", request, ct);

    public Task<JsonNode?> LoginAsync(string username, string password, string captchaToken, CancellationToken ct = default)
        => SubmitAsync("/auth/login", new { username, password, captcha_token = captchaToken }, null, ct);

    public Task<JsonNode?> Verify2faAsync(string challengeToken, string code, string? backupCode = null, CancellationToken ct = default)
    {
        object body = backupCode != null ? new { code, backup_code = backupCode } : new { code };
        return SubmitAsync("/auth/2fa/verify", body,
            new Dictionary<string, string> { ["authorization"] = $"Bearer {challengeToken}" }, ct);
    }

    public Task<JsonNode?> VerifyEmailAsync(string token, CancellationToken ct = default)
        => Transport.PostAsync("/auth/verify", "none", new { token }, ct);

    public Task<JsonNode?> ResendVerificationAsync(string identifier, CancellationToken ct = default)
        => Transport.PostAsync("/auth/resend-verification", "none", new { identifier }, ct);

    public async Task<JsonNode?> LogoutAsync(CancellationToken ct = default)
    {
        var result = await Transport.PostAsync("/auth/logout", "session", null, ct).ConfigureAwait(false);
        Transport.SetSessionToken(null);
        return result;
    }
}

/// <summary>OAuth 2.0 provider flow + self-service app management.</summary>
public sealed class OAuthResource : Resource
{
    internal OAuthResource(Transport t) : base(t) { }

    /// <summary>Generate a PKCE verifier/challenge pair (S256).</summary>
    public static (string Verifier, string Challenge, string Method) CreatePkcePair()
    {
        var random = RandomNumberGenerator.GetBytes(32);
        var verifier = Base64Url(random);
        var challenge = Base64Url(SHA256.HashData(Encoding.ASCII.GetBytes(verifier)));
        return (verifier, challenge, "S256");
    }

    /// <summary>Build the <c>/oauth/authorize</c> URL to redirect a user to.</summary>
    public string AuthorizeUrl(string clientId, string redirectUri, IEnumerable<string>? scope = null,
        string? state = null, string? codeChallenge = null, string codeChallengeMethod = "S256")
    {
        var query = new List<string>
        {
            "response_type=code",
            "client_id=" + Uri.EscapeDataString(clientId),
            "redirect_uri=" + Uri.EscapeDataString(redirectUri),
        };
        if (scope != null) query.Add("scope=" + Uri.EscapeDataString(string.Join(" ", scope)));
        if (state != null) query.Add("state=" + Uri.EscapeDataString(state));
        if (codeChallenge != null)
        {
            query.Add("code_challenge=" + Uri.EscapeDataString(codeChallenge));
            query.Add("code_challenge_method=" + Uri.EscapeDataString(codeChallengeMethod));
        }
        return Transport.BaseUrl + "/oauth/authorize?" + string.Join("&", query);
    }

    /// <summary>Exchange an authorization code for an access token.</summary>
    public Task<JsonNode?> ExchangeTokenAsync(IDictionary<string, string> parameters, CancellationToken ct = default)
    {
        var form = new Dictionary<string, string> { ["grant_type"] = "authorization_code" };
        foreach (var kv in parameters) form[kv.Key] = kv.Value;
        return FormAsync("/oauth/token", form, ct);
    }

    public Task<JsonNode?> UserInfoAsync(string accessToken, CancellationToken ct = default)
        => Transport.RequestJsonAsync(HttpMethod.Get, "/oauth/userinfo", new RequestOptions
        {
            Auth = "none",
            Headers = new Dictionary<string, string> { ["authorization"] = $"Bearer {accessToken}" },
        }, ct);

    public Task<JsonNode?> RevokeTokenAsync(string token, CancellationToken ct = default)
        => FormAsync("/oauth/revoke", new Dictionary<string, string> { ["token"] = token }, ct);

    public Task<JsonNode?> ListAppsAsync(CancellationToken ct = default)
        => Transport.GetAsync("/api/me/oauth-apps", "session", null, ct);

    public Task<JsonNode?> CreateAppAsync(object request, CancellationToken ct = default)
        => Transport.PostAsync("/api/me/oauth-apps", "session", request, ct);

    public Task<JsonNode?> GetAppAsync(string clientId, CancellationToken ct = default)
        => Transport.GetAsync($"/api/me/oauth-apps/{Enc(clientId)}", "session", null, ct);

    public Task<JsonNode?> UpdateAppAsync(string clientId, object patch, CancellationToken ct = default)
        => Transport.MethodAsync(HttpMethod.Patch, $"/api/me/oauth-apps/{Enc(clientId)}", "session", patch, ct);

    public Task<JsonNode?> DeleteAppAsync(string clientId, CancellationToken ct = default)
        => Transport.DeleteAsync($"/api/me/oauth-apps/{Enc(clientId)}", "session", ct);

    public Task<JsonNode?> RotateSecretAsync(string clientId, CancellationToken ct = default)
        => Transport.PostAsync($"/api/me/oauth-apps/{Enc(clientId)}/rotate-secret", "session", null, ct);

    public Task<JsonNode?> ConnectedAppsAsync(CancellationToken ct = default)
        => Transport.GetAsync("/api/me/connected-apps", "session", null, ct);

    public Task<JsonNode?> RevokeConnectedAppAsync(string clientId, CancellationToken ct = default)
        => Transport.DeleteAsync($"/api/me/connected-apps/{Enc(clientId)}", "session", ct);

    private Task<JsonNode?> FormAsync(string path, IDictionary<string, string> fields, CancellationToken ct)
    {
        var encoded = string.Join("&", fields.Select(kv =>
            $"{Uri.EscapeDataString(kv.Key)}={Uri.EscapeDataString(kv.Value)}"));
        return Transport.RequestJsonAsync(HttpMethod.Post, path, new RequestOptions
        {
            Auth = "none",
            Body = Encoding.UTF8.GetBytes(encoded),
            ContentType = "application/x-www-form-urlencoded",
        }, ct);
    }

    private static string Base64Url(byte[] data) =>
        Convert.ToBase64String(data).TrimEnd('=').Replace('+', '-').Replace('/', '_');
}
