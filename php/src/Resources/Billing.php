<?php

declare(strict_types=1);

namespace Airforce\Resources;

use Airforce\Transport;

/** Billing, plans, and public analytics. */
final class Billing
{
    public function __construct(private Transport $t)
    {
    }

    /** @param array<string,mixed> $request */
    public function createCheckout(array $request): mixed
    {
        return $this->t->post('/api/creem/create-checkout', 'session', $request);
    }

    /** @param array<string,mixed> $request */
    public function createCryptoInvoice(array $request): mixed
    {
        return $this->t->post('/api/create-nowpayments-invoice', 'session', $request);
    }

    public function createPortalSession(): mixed
    {
        return $this->t->post('/api/create-portal-session', 'session', []);
    }

    public function analytics(): mixed
    {
        return $this->t->get('/v1/analytics', 'none');
    }
}
