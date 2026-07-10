using System.Text.Json.Nodes;

namespace Airforce;

/// <summary>Notification preferences, the in-app feed, and delivery-channel linking —
/// <c>/api/me/notification-prefs</c>, <c>/api/me/notifications</c>, <c>/api/me/channels</c>.
/// All endpoints require a session token.</summary>
public sealed class NotificationsResource : Resource
{
    internal NotificationsResource(Transport t) : base(t) { }

    public Task<JsonNode?> GetPrefsAsync(CancellationToken ct = default)
        => Transport.GetAsync("/api/me/notification-prefs", "session", null, ct);

    /// <summary>Partially update preferences: an absent field is unchanged;
    /// <c>quiet_hours: null</c> clears quiet hours. Unknown channel ids in
    /// <c>routing</c> are dropped server-side. Returns the updated preferences.</summary>
    public Task<JsonNode?> UpdatePrefsAsync(object patch, CancellationToken ct = default)
        => Transport.MethodAsync(HttpMethod.Patch, "/api/me/notification-prefs", "session", patch, ct);

    /// <summary>List feed items, newest first — <c>{items, unread}</c>. <paramref name="limit"/>
    /// is 1–100 (default 30); <paramref name="before"/> is the <c>created_at</c> cursor of
    /// the last item from the previous page.</summary>
    public Task<JsonNode?> ListAsync(int? limit = null, string? before = null, CancellationToken ct = default)
    {
        var query = new Dictionary<string, string?>
        {
            ["limit"] = limit?.ToString(),
            ["before"] = before,
        };
        return Transport.GetAsync("/api/me/notifications", "session", query, ct);
    }

    /// <summary>Mark specific feed items read. Returns <c>{updated, unread}</c>.</summary>
    public Task<JsonNode?> MarkReadAsync(IEnumerable<string> ids, CancellationToken ct = default)
        => Transport.PostAsync("/api/me/notifications/read", "session", new { ids }, ct);

    /// <summary>Mark every feed item read. Returns <c>{updated, unread}</c>.</summary>
    public Task<JsonNode?> MarkAllReadAsync(CancellationToken ct = default)
        => Transport.PostAsync("/api/me/notifications/read", "session", new { all = true }, ct);

    /// <summary>List linked delivery-channel identities plus the linkable channel ids —
    /// <c>{identities, available_channels}</c>.</summary>
    public Task<JsonNode?> ChannelsAsync(CancellationToken ct = default)
        => Transport.GetAsync("/api/me/channels", "session", null, ct);

    /// <summary>Start linking a delivery channel. The verification code is delivered
    /// through the channel itself and expires after 30 minutes. Bot channels accept an
    /// empty <paramref name="address"/> and answer with a one-time link code / deep link
    /// (<c>{status: "link_ready", code, deep_link?, expires_minutes}</c>) instead of
    /// <c>{status: "verification_sent"}</c>.</summary>
    public Task<JsonNode?> LinkChannelAsync(string channel, string address, string? display = null,
        CancellationToken ct = default)
    {
        object body = display != null ? new { channel, address, display } : new { channel, address };
        return Transport.PostAsync("/api/me/channels", "session", body, ct);
    }

    /// <summary>Complete channel verification with the delivered code (400 on an invalid
    /// or expired code).</summary>
    public Task<JsonNode?> VerifyChannelAsync(string channel, string code, CancellationToken ct = default)
        => Transport.PostAsync("/api/me/channels/verify", "session", new { channel, code }, ct);

    /// <summary>Unlink/revoke a channel identity.</summary>
    public Task<JsonNode?> UnlinkChannelAsync(string channel, CancellationToken ct = default)
        => Transport.DeleteAsync($"/api/me/channels/{Enc(channel)}", "session", ct);
}
