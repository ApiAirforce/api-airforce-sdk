<?php

declare(strict_types=1);

namespace Airforce\Resources;

use Airforce\Transport;

/** Two-factor authentication — /api/2fa/*. */
final class TwoFactor
{
    public function __construct(private Transport $t)
    {
    }

    public function setupInit(): mixed
    {
        return $this->t->post('/api/2fa/setup-init', 'session');
    }
    public function setupVerify(string $code): mixed
    {
        return $this->t->post('/api/2fa/setup-verify', 'session', ['code' => $code]);
    }
    public function disable(string $password, string $code): mixed
    {
        return $this->t->post('/api/2fa/disable', 'session', ['password' => $password, 'code' => $code]);
    }
    public function regenerateBackupCodes(string $code): mixed
    {
        return $this->t->post('/api/2fa/regenerate-backup-codes', 'session', ['code' => $code]);
    }
    public function verifyStepUp(string $code): mixed
    {
        return $this->t->post('/api/2fa/verify-step-up', 'session', ['code' => $code]);
    }
    public function stepUpStatus(): mixed
    {
        return $this->t->get('/api/2fa/step-up-status', 'session');
    }
}
