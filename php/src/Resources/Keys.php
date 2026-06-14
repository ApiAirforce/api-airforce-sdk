<?php

declare(strict_types=1);

namespace Airforce\Resources;

use Airforce\Transport;

/** API key provisioning — /v1/keys. */
final class Keys
{
    public function __construct(private Transport $t)
    {
    }

    /** @param array<string,mixed> $request */
    public function create(array $request): mixed
    {
        return $this->t->post('/v1/keys', 'api_key', $request);
    }

    public function list(): mixed
    {
        $res = $this->t->get('/v1/keys', 'api_key');
        return is_array($res) && isset($res['keys']) ? $res['keys'] : $res;
    }

    /** @param array<string,mixed> $request */
    public function update(string $key, array $request): mixed
    {
        return $this->t->method('PATCH', '/v1/keys/' . rawurlencode($key), 'api_key', $request);
    }

    public function delete(string $key): mixed
    {
        return $this->t->delete('/v1/keys/' . rawurlencode($key), 'api_key');
    }
}
