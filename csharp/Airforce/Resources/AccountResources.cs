using System.Text.Json.Nodes;

namespace Airforce;

/// <summary>Account self-service — <c>/api/me</c>, <c>/api/user/*</c>.</summary>
public sealed class AccountResource : Resource
{
    internal AccountResource(Transport t) : base(t) { }

    public Task<JsonNode?> MeAsync(CancellationToken ct = default) => Transport.GetAsync("/api/me", "session", null, ct);
    public Task<JsonNode?> UsageAsync(CancellationToken ct = default) => Transport.GetAsync("/api/usage", "session", null, ct);
    public Task<JsonNode?> MyUsageAsync(CancellationToken ct = default) => Transport.GetAsync("/api/my-usage", "session", null, ct);

    public Task<JsonNode?> UpdateAsync(object body, CancellationToken ct = default)
        => Transport.MethodAsync(HttpMethod.Put, "/api/user/update", "session", body, ct);

    public Task<JsonNode?> RequestPasswordResetAsync(string email, string? locale = null, CancellationToken ct = default)
    {
        object body = locale != null ? new { email, locale } : new { email };
        return Transport.PostAsync("/api/auth/request-password-reset", "none", body, ct);
    }

    public Task<JsonNode?> ResetPasswordAsync(string token, string newPassword, CancellationToken ct = default)
        => Transport.PostAsync("/api/auth/reset-password", "none", new { token, new_password = newPassword }, ct);

    public Task<JsonNode?> ReferralCodeAsync(CancellationToken ct = default)
        => Transport.GetAsync("/api/referral/code", "session", null, ct);

    public Task<JsonNode?> ReferredUsersAsync(CancellationToken ct = default)
        => Transport.GetAsync("/api/referral/referred-users", "session", null, ct);

    public Task<JsonNode?> GetPriceCapsAsync(CancellationToken ct = default)
        => Transport.GetAsync("/api/user/price-caps", "session", null, ct);

    public Task<JsonNode?> SetPriceCapsAsync(object caps, CancellationToken ct = default)
        => Transport.MethodAsync(HttpMethod.Put, "/api/user/price-caps", "session", new { caps }, ct);

    public Task<JsonNode?> DeletePriceCapAsync(string model, CancellationToken ct = default)
        => Transport.DeleteAsync($"/api/user/price-caps/{Enc(model)}", "session", ct);

    public Task<JsonNode?> GetModelAliasesAsync(CancellationToken ct = default)
        => Transport.GetAsync("/api/user/model-aliases", "session", null, ct);

    public Task<JsonNode?> SetModelAliasAsync(string alias, string model, CancellationToken ct = default)
        => Transport.MethodAsync(HttpMethod.Put, "/api/user/model-aliases", "session", new { alias, model }, ct);

    public Task<JsonNode?> SetModelAliasesBatchAsync(object aliases, CancellationToken ct = default)
        => Transport.MethodAsync(HttpMethod.Put, "/api/user/model-aliases/batch", "session", aliases, ct);

    public Task<JsonNode?> DeleteModelAliasAsync(string alias, CancellationToken ct = default)
        => Transport.DeleteAsync($"/api/user/model-aliases/{Enc(alias)}", "session", ct);

    public Task<JsonNode?> GetModelDefaultsAsync(CancellationToken ct = default)
        => Transport.GetAsync("/api/user/model-defaults", "session", null, ct);

    public Task<JsonNode?> SetModelDefaultAsync(string model, object def, CancellationToken ct = default)
        => Transport.MethodAsync(HttpMethod.Put, $"/api/user/model-defaults/{Enc(model)}", "session", def, ct);

    public Task<JsonNode?> DeleteModelDefaultAsync(string model, CancellationToken ct = default)
        => Transport.DeleteAsync($"/api/user/model-defaults/{Enc(model)}", "session", ct);

    public Task<JsonNode?> GetSmartRoutingAsync(CancellationToken ct = default)
        => Transport.GetAsync("/api/user/smart-routing", "api_key", null, ct);

    public Task<JsonNode?> SetSmartRoutingAsync(object groups, CancellationToken ct = default)
        => Transport.MethodAsync(HttpMethod.Put, "/api/user/smart-routing", "api_key", new { groups }, ct);

    public Task<JsonNode?> TestSmartRoutingAsync(string model, CancellationToken ct = default)
        => Transport.GetAsync("/api/user/smart-routing/test", "api_key",
            new Dictionary<string, string?> { ["model"] = model }, ct);

    public Task<JsonNode?> GetChannelPrefsAsync(CancellationToken ct = default)
        => Transport.GetAsync("/api/user/channel-prefs", "api_key", null, ct);

    public Task<JsonNode?> SetChannelPinsAsync(object pins, CancellationToken ct = default)
        => Transport.MethodAsync(HttpMethod.Put, "/api/user/channel-prefs", "api_key", pins, ct);

    public Task<JsonNode?> SessionsAsync(CancellationToken ct = default)
        => Transport.GetAsync("/api/me/sessions", "session", null, ct);

    public Task<JsonNode?> RevokeSessionAsync(string jti, CancellationToken ct = default)
        => Transport.DeleteAsync($"/api/me/sessions/{Enc(jti)}", "session", ct);

    public Task<JsonNode?> RevokeOtherSessionsAsync(CancellationToken ct = default)
        => Transport.DeleteAsync("/api/me/sessions", "session", ct);

    public Task<JsonNode?> LoginHistoryAsync(int? limit = null, CancellationToken ct = default)
    {
        var query = limit.HasValue
            ? new Dictionary<string, string?> { ["limit"] = limit.Value.ToString() }
            : null;
        return Transport.GetAsync("/api/me/login-history", "session", query, ct);
    }

    public Task<JsonNode?> ResetApiKeyAsync(CancellationToken ct = default)
        => Transport.PostAsync("/api/user/reset-api-key", "session", null, ct);

    public Task<JsonNode?> SetPrimaryAllowedIpsAsync(IEnumerable<string> ips, CancellationToken ct = default)
        => Transport.MethodAsync(HttpMethod.Put, "/api/user/primary-allowed-ips", "session", new { allowed_ips = ips }, ct);

    public Task<JsonNode?> SetBackupPoolEnabledAsync(bool enabled, CancellationToken ct = default)
        => Transport.MethodAsync(HttpMethod.Put, "/api/user/backup-pool-enabled", "api_key", new { enabled }, ct);

    public Task<JsonNode?> TogglePayAsYouGoAsync(CancellationToken ct = default)
        => Transport.PostAsync("/api/pay-as-you-go/toggle", "session", null, ct);
}

/// <summary>API key provisioning — <c>/v1/keys</c>.</summary>
public sealed class KeysResource : Resource
{
    internal KeysResource(Transport t) : base(t) { }

    public Task<JsonNode?> CreateAsync(object request, CancellationToken ct = default)
        => Transport.PostAsync("/v1/keys", "api_key", request, ct);

    public async Task<JsonNode?> ListAsync(CancellationToken ct = default)
    {
        var res = await Transport.GetAsync("/v1/keys", "api_key", null, ct).ConfigureAwait(false);
        return res?["keys"] ?? res;
    }

    public Task<JsonNode?> UpdateAsync(string key, object request, CancellationToken ct = default)
        => Transport.MethodAsync(HttpMethod.Patch, $"/v1/keys/{Enc(key)}", "api_key", request, ct);

    public Task<JsonNode?> DeleteAsync(string key, CancellationToken ct = default)
        => Transport.DeleteAsync($"/v1/keys/{Enc(key)}", "api_key", ct);
}

/// <summary>Billing, plans, and public analytics.</summary>
public sealed class BillingResource : Resource
{
    internal BillingResource(Transport t) : base(t) { }

    public Task<JsonNode?> CreateCheckoutAsync(object request, CancellationToken ct = default)
        => Transport.PostAsync("/api/creem/create-checkout", "session", request, ct);

    public Task<JsonNode?> CreateCryptoInvoiceAsync(object request, CancellationToken ct = default)
        => Transport.PostAsync("/api/create-nowpayments-invoice", "session", request, ct);

    public Task<JsonNode?> CreatePortalSessionAsync(CancellationToken ct = default)
        => Transport.PostAsync("/api/create-portal-session", "session", new { }, ct);

    public Task<JsonNode?> AnalyticsAsync(CancellationToken ct = default)
        => Transport.GetAsync("/v1/analytics", "none", null, ct);
}
