<?php

declare(strict_types=1);

namespace Airforce\Resources;

use Airforce\Transport;

/** Image generation — POST /v1/images/generations. */
final class Images
{
    public function __construct(private Transport $t)
    {
    }

    /** @param array<string,mixed> $request */
    public function generate(array $request): mixed
    {
        return $this->t->post('/v1/images/generations', 'api_key', $request);
    }
}
