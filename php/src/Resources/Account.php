<?php

declare(strict_types=1);

namespace Airforce\Resources;

use Airforce\Transport;

/** Account self-service — /api/me, /api/user/*. */
final class Account
{
    public function __construct(private Transport $t)
    {
    }

    public function me(): mixed
    {
        return $this->t->get('/api/me', 'session');
    }
    public function usage(): mixed
    {
        return $this->t->get('/api/usage', 'session');
    }
    public function myUsage(): mixed
    {
        return $this->t->get('/api/my-usage', 'session');
    }

    /** @param array<string,mixed> $body */
    public function update(array $body): mixed
    {
        return $this->t->method('PUT', '/api/user/update', 'session', $body);
    }

    public function requestPasswordReset(string $email, ?string $locale = null): mixed
    {
        $body = ['email' => $email];
        if ($locale !== null) {
            $body['locale'] = $locale;
        }
        return $this->t->post('/api/auth/request-password-reset', 'none', $body);
    }

    public function resetPassword(string $token, string $newPassword): mixed
    {
        return $this->t->post('/api/auth/reset-password', 'none', ['token' => $token, 'new_password' => $newPassword]);
    }

    public function referralCode(): mixed
    {
        return $this->t->get('/api/referral/code', 'session');
    }
    public function referredUsers(): mixed
    {
        return $this->t->get('/api/referral/referred-users', 'session');
    }

    public function getPriceCaps(): mixed
    {
        return $this->t->get('/api/user/price-caps', 'session');
    }
    /** @param array<string,mixed> $caps */
    public function setPriceCaps(array $caps): mixed
    {
        return $this->t->method('PUT', '/api/user/price-caps', 'session', ['caps' => $caps]);
    }
    public function deletePriceCap(string $model): mixed
    {
        return $this->t->delete('/api/user/price-caps/' . rawurlencode($model), 'session');
    }

    public function getModelAliases(): mixed
    {
        return $this->t->get('/api/user/model-aliases', 'session');
    }
    public function setModelAlias(string $alias, string $model): mixed
    {
        return $this->t->method('PUT', '/api/user/model-aliases', 'session', ['alias' => $alias, 'model' => $model]);
    }
    /** @param list<array{alias:string,model:string}> $aliases */
    public function setModelAliasesBatch(array $aliases): mixed
    {
        return $this->t->method('PUT', '/api/user/model-aliases/batch', 'session', $aliases);
    }
    public function deleteModelAlias(string $alias): mixed
    {
        return $this->t->delete('/api/user/model-aliases/' . rawurlencode($alias), 'session');
    }

    public function getModelDefaults(): mixed
    {
        return $this->t->get('/api/user/model-defaults', 'session');
    }
    /** @param array<string,mixed> $def */
    public function setModelDefault(string $model, array $def): mixed
    {
        return $this->t->method('PUT', '/api/user/model-defaults/' . rawurlencode($model), 'session', $def);
    }
    public function deleteModelDefault(string $model): mixed
    {
        return $this->t->delete('/api/user/model-defaults/' . rawurlencode($model), 'session');
    }

    public function getSmartRouting(): mixed
    {
        return $this->t->get('/api/user/smart-routing', 'api_key');
    }
    /** @param array<string,mixed> $groups */
    public function setSmartRouting(array $groups): mixed
    {
        return $this->t->method('PUT', '/api/user/smart-routing', 'api_key', ['groups' => $groups]);
    }
    public function testSmartRouting(string $model): mixed
    {
        return $this->t->get('/api/user/smart-routing/test', 'api_key', ['model' => $model]);
    }

    public function getChannelPrefs(): mixed
    {
        return $this->t->get('/api/user/channel-prefs', 'api_key');
    }
    /** @param array<string,string> $pins */
    public function setChannelPins(array $pins): mixed
    {
        return $this->t->method('PUT', '/api/user/channel-prefs', 'api_key', $pins);
    }

    public function sessions(): mixed
    {
        return $this->t->get('/api/me/sessions', 'session');
    }
    public function revokeSession(string $jti): mixed
    {
        return $this->t->delete('/api/me/sessions/' . rawurlencode($jti), 'session');
    }
    public function revokeOtherSessions(): mixed
    {
        return $this->t->delete('/api/me/sessions', 'session');
    }

    public function loginHistory(?int $limit = null): mixed
    {
        return $this->t->get('/api/me/login-history', 'session', $limit !== null ? ['limit' => (string) $limit] : null);
    }

    public function resetApiKey(): mixed
    {
        return $this->t->post('/api/user/reset-api-key', 'session');
    }
    /** @param list<string> $ips */
    public function setPrimaryAllowedIps(array $ips): mixed
    {
        return $this->t->method('PUT', '/api/user/primary-allowed-ips', 'session', ['allowed_ips' => $ips]);
    }
    public function setBackupPoolEnabled(bool $enabled): mixed
    {
        return $this->t->method('PUT', '/api/user/backup-pool-enabled', 'api_key', ['enabled' => $enabled]);
    }
    public function togglePayAsYouGo(): mixed
    {
        return $this->t->post('/api/pay-as-you-go/toggle', 'session');
    }
}
