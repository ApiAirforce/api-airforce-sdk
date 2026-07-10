<?php

declare(strict_types=1);

namespace Airforce\Resources;

use Airforce\Transport;

/**
 * Organization self-service — /api/org/*. All session-token authenticated; the org
 * context is implicit via the caller's membership. Roles: owner ⊃ admin ⊃ member.
 */
final class Org
{
    public function __construct(private Transport $t)
    {
    }

    /** The caller's org + own role: `{org, role}`. 404 `no_org` when the caller has none. */
    public function get(): mixed
    {
        return $this->t->get('/api/org', 'session');
    }

    /** @param array<string,mixed> $patch `{name?}` (owner only) */
    public function update(array $patch): mixed
    {
        return $this->t->method('PATCH', '/api/org', 'session', $patch);
    }

    /** @param array<string,mixed> $patch `{tenant_id?, verified_domain?, enforced?}` — `''` clears a field, omit = unchanged (owner only) */
    public function updateSso(array $patch): mixed
    {
        return $this->t->method('PATCH', '/api/org/sso', 'session', $patch);
    }

    /** List members (owner/admin only; returns the `members` array). */
    public function members(): mixed
    {
        $res = $this->t->get('/api/org/members', 'session');
        return is_array($res) && isset($res['members']) ? $res['members'] : $res;
    }

    /** @param array<string,mixed> $patch `{role?: 'admin'|'member', status?: 'active'|'suspended'}` */
    public function updateMember(int|string $userId, array $patch): mixed
    {
        return $this->t->method('PATCH', '/api/org/members/' . rawurlencode((string) $userId), 'session', $patch);
    }

    /** Remove a member (owner/admin) or leave the org (self). */
    public function removeMember(int|string $userId): mixed
    {
        return $this->t->delete('/api/org/members/' . rawurlencode((string) $userId), 'session');
    }

    /** List pending invites (owner/admin only; returns the `invites` array). */
    public function invites(): mixed
    {
        $res = $this->t->get('/api/org/invites', 'session');
        return is_array($res) && isset($res['invites']) ? $res['invites'] : $res;
    }

    /** Invite by email (7-day expiry; admin invites are owner-only). Returns `{invite, invite_url}`. */
    public function createInvite(string $email, ?string $role = null): mixed
    {
        $body = ['email' => $email];
        if ($role !== null) {
            $body['role'] = $role;
        }
        return $this->t->post('/api/org/invites', 'session', $body);
    }

    /** Accept an invite (any logged-in user without an org; email must match and be verified). */
    public function acceptInvite(string $token): mixed
    {
        return $this->t->post('/api/org/invites/accept', 'session', ['token' => $token]);
    }

    public function revokeInvite(string $id): mixed
    {
        return $this->t->delete('/api/org/invites/' . rawurlencode($id), 'session');
    }

    /** List org keys — owner/admin: all; member: own only (returns the `keys` array, masked). */
    public function keys(): mixed
    {
        $res = $this->t->get('/api/org/keys', 'session');
        return is_array($res) && isset($res['keys']) ? $res['keys'] : $res;
    }

    /**
     * Create a key for a member (owner/admin); bills the org owner's wallet. The full
     * key is shown only in this response.
     *
     * @param array<string,mixed> $request `{member_user_id, label?, credit_allowance?, limit_reset?, rpm_limit?, allowed_models?, ...}`
     */
    public function createKey(array $request): mixed
    {
        return $this->t->post('/api/org/keys', 'session', $request);
    }

    /** @param array<string,mixed> $patch same fields as create plus `disabled?` (`member_user_id` not changeable) */
    public function updateKey(string $id, array $patch): mixed
    {
        return $this->t->method('PATCH', '/api/org/keys/' . rawurlencode($id), 'session', $patch);
    }

    public function deleteKey(string $id): mixed
    {
        return $this->t->delete('/api/org/keys/' . rawurlencode($id), 'session');
    }

    /**
     * Aggregate + per-member + per-key + daily-timeseries usage. `$from`/`$to` are unix
     * seconds (default: last 30 days); cost values are cents. Members are scoped to self.
     */
    public function usage(?int $from = null, ?int $to = null, int|string|null $memberUserId = null, ?string $keyId = null): mixed
    {
        $query = [];
        if ($from !== null) {
            $query['from'] = (string) $from;
        }
        if ($to !== null) {
            $query['to'] = (string) $to;
        }
        if ($memberUserId !== null) {
            $query['member_user_id'] = (string) $memberUserId;
        }
        if ($keyId !== null) {
            $query['key_id'] = $keyId;
        }
        return $this->t->get('/api/org/usage', 'session', $query ?: null);
    }
}
