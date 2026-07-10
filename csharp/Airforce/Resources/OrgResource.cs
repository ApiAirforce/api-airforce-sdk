using System.Text.Json.Nodes;

namespace Airforce;

/// <summary>Organization self-service — <c>/api/org/*</c>. All endpoints require a session
/// token; the org context is implicit via the caller's membership (one org per user).
/// Roles: owner > admin > member. Callers without an org get 404 <c>no_org</c>; suspended
/// members get 403 <c>membership_inactive</c>.</summary>
public sealed class OrgResource : Resource
{
    internal OrgResource(Transport t) : base(t) { }

    /// <summary>The caller's org plus their own role — <c>{org, role}</c>.</summary>
    public Task<JsonNode?> GetAsync(CancellationToken ct = default)
        => Transport.GetAsync("/api/org", "session", null, ct);

    /// <summary>Rename the org (owner only; <c>{name}</c>, 1–100 chars).</summary>
    public Task<JsonNode?> UpdateAsync(object patch, CancellationToken ct = default)
        => Transport.MethodAsync(HttpMethod.Patch, "/api/org", "session", patch, ct);

    /// <summary>Owner-only SSO config — <c>{tenant_id?, verified_domain?, enforced?}</c>.
    /// An empty string clears a field; omit = unchanged. 409 when the tenant or domain is
    /// already claimed by another org.</summary>
    public Task<JsonNode?> UpdateSsoAsync(object patch, CancellationToken ct = default)
        => Transport.MethodAsync(HttpMethod.Patch, "/api/org/sso", "session", patch, ct);

    /// <summary>List members (owner/admin only). Returns the <c>members</c> array.</summary>
    public async Task<JsonNode?> MembersAsync(CancellationToken ct = default)
    {
        var res = await Transport.GetAsync("/api/org/members", "session", null, ct).ConfigureAwait(false);
        return res?["members"] ?? res;
    }

    /// <summary>Change a member's role (owner only) and/or status — <c>{role?, status?}</c>.
    /// Suspending disables the member's org keys; the owner row is immutable; admins may
    /// only manage plain members.</summary>
    public Task<JsonNode?> UpdateMemberAsync(string userId, object patch, CancellationToken ct = default)
        => Transport.MethodAsync(HttpMethod.Patch, $"/api/org/members/{Enc(userId)}", "session", patch, ct);

    /// <summary>Remove a member (owner/admin) or leave the org (self); the owner cannot be
    /// removed. The member's org keys are disabled.</summary>
    public Task<JsonNode?> RemoveMemberAsync(string userId, CancellationToken ct = default)
        => Transport.DeleteAsync($"/api/org/members/{Enc(userId)}", "session", ct);

    /// <summary>List pending invites (owner/admin). Returns the <c>invites</c> array.</summary>
    public async Task<JsonNode?> InvitesAsync(CancellationToken ct = default)
    {
        var res = await Transport.GetAsync("/api/org/invites", "session", null, ct).ConfigureAwait(false);
        return res?["invites"] ?? res;
    }

    /// <summary>Invite by email (7-day expiry; admin invites are owner-only). Returns
    /// <c>{invite, invite_url}</c> — mail delivery is best-effort, the URL is the reliable
    /// path. 429 on invite cooldown/cap.</summary>
    public Task<JsonNode?> CreateInviteAsync(string email, string? role = null, CancellationToken ct = default)
    {
        object body = role != null ? new { email, role } : new { email };
        return Transport.PostAsync("/api/org/invites", "session", body, ct);
    }

    /// <summary>Accept an invite (any logged-in user without an org). The account email
    /// must match the invite and be verified. Returns <c>{org, role}</c>; 409
    /// <c>already_in_org</c>, 410 when expired.</summary>
    public Task<JsonNode?> AcceptInviteAsync(string token, CancellationToken ct = default)
        => Transport.PostAsync("/api/org/invites/accept", "session", new { token }, ct);

    /// <summary>Revoke a pending invite (owner/admin).</summary>
    public Task<JsonNode?> RevokeInviteAsync(string id, CancellationToken ct = default)
        => Transport.DeleteAsync($"/api/org/invites/{Enc(id)}", "session", ct);

    /// <summary>List org keys — owner/admin: all; member: own only. Keys are masked
    /// (<c>masked_key</c>/<c>key_prefix</c>/<c>key_last4</c>). Returns the <c>keys</c> array.</summary>
    public async Task<JsonNode?> KeysAsync(CancellationToken ct = default)
    {
        var res = await Transport.GetAsync("/api/org/keys", "session", null, ct).ConfigureAwait(false);
        return res?["keys"] ?? res;
    }

    /// <summary>Create a key for a member (owner/admin) — the request needs
    /// <c>member_user_id</c>; billed to the org owner's wallet. Returns <c>{item}</c> with
    /// the full key, shown only once.</summary>
    public Task<JsonNode?> CreateKeyAsync(object request, CancellationToken ct = default)
        => Transport.PostAsync("/api/org/keys", "session", request, ct);

    /// <summary>Update an org key (owner/admin); same fields as create plus
    /// <c>disabled?</c> (<c>member_user_id</c> is not changeable).</summary>
    public Task<JsonNode?> UpdateKeyAsync(string id, object patch, CancellationToken ct = default)
        => Transport.MethodAsync(HttpMethod.Patch, $"/api/org/keys/{Enc(id)}", "session", patch, ct);

    public Task<JsonNode?> DeleteKeyAsync(string id, CancellationToken ct = default)
        => Transport.DeleteAsync($"/api/org/keys/{Enc(id)}", "session", ct);

    /// <summary>Aggregate + per-member + per-key + daily timeseries usage. <paramref name="from"/>
    /// and <paramref name="to"/> are unix seconds (default: last 30 days); cost values are
    /// cents. Members see only their own usage.</summary>
    public Task<JsonNode?> UsageAsync(long? from = null, long? to = null, string? memberUserId = null,
        string? keyId = null, CancellationToken ct = default)
    {
        var query = new Dictionary<string, string?>
        {
            ["from"] = from?.ToString(),
            ["to"] = to?.ToString(),
            ["member_user_id"] = memberUserId,
            ["key_id"] = keyId,
        };
        return Transport.GetAsync("/api/org/usage", "session", query, ct);
    }
}
