<?php

declare(strict_types=1);

namespace Airforce\Resources;

use Airforce\Transport;

/**
 * Notification preferences, the in-app feed, and delivery-channel linking —
 * /api/me/notification-prefs, /api/me/notifications, /api/me/channels.
 */
final class Notifications
{
    public function __construct(private Transport $t)
    {
    }

    public function getPrefs(): mixed
    {
        return $this->t->get('/api/me/notification-prefs', 'session');
    }

    /** @param array<string,mixed> $patch partial prefs — absent field = unchanged; `quiet_hours: null` clears */
    public function updatePrefs(array $patch): mixed
    {
        return $this->t->method('PATCH', '/api/me/notification-prefs', 'session', $patch);
    }

    /**
     * In-app feed, newest first: `{items, unread}`. `$before` is a `created_at` cursor
     * for paging; `$limit` is 1–100 (default 30).
     */
    public function list(?int $limit = null, ?string $before = null): mixed
    {
        $query = [];
        if ($limit !== null) {
            $query['limit'] = (string) $limit;
        }
        if ($before !== null) {
            $query['before'] = $before;
        }
        return $this->t->get('/api/me/notifications', 'session', $query ?: null);
    }

    /** @param list<string> $ids feed item ids to mark read; returns `{updated, unread}` */
    public function markRead(array $ids): mixed
    {
        return $this->t->post('/api/me/notifications/read', 'session', ['ids' => $ids]);
    }

    public function markAllRead(): mixed
    {
        return $this->t->post('/api/me/notifications/read', 'session', ['all' => true]);
    }

    /** Linked delivery-channel identities + linkable channel ids: `{identities, available_channels}`. */
    public function channels(): mixed
    {
        return $this->t->get('/api/me/channels', 'session');
    }

    /**
     * Start linking a channel. The verification code is delivered through the channel
     * itself (30-min expiry). Bot channels accept an empty `$address` and return a
     * one-time link code / deep link instead (`status: 'link_ready'`).
     */
    public function linkChannel(string $channel, string $address = '', ?string $display = null): mixed
    {
        $body = ['channel' => $channel, 'address' => $address];
        if ($display !== null) {
            $body['display'] = $display;
        }
        return $this->t->post('/api/me/channels', 'session', $body);
    }

    /** Complete channel verification with the delivered code (400 on invalid/expired). */
    public function verifyChannel(string $channel, string $code): mixed
    {
        return $this->t->post('/api/me/channels/verify', 'session', ['channel' => $channel, 'code' => $code]);
    }

    public function unlinkChannel(string $channel): mixed
    {
        return $this->t->delete('/api/me/channels/' . rawurlencode($channel), 'session');
    }
}
