<?php

declare(strict_types=1);

namespace Airforce\Resources;

use Airforce\Transport;

/** Model catalog / discovery. */
final class Models
{
    public function __construct(private Transport $t)
    {
    }

    /** List public models (returns the `data` array). */
    public function list(bool $channels = false): mixed
    {
        $res = $this->t->get('/v1/models', 'none', $channels ? ['channels' => '1'] : null);
        return is_array($res) && isset($res['data']) ? $res['data'] : $res;
    }

    public function detail(string $model): mixed
    {
        return $this->t->get('/api/models/' . rawurlencode($model) . '/detail', 'none');
    }

    public function allowedParams(string $model): mixed
    {
        return $this->t->get('/api/models/' . rawurlencode($model) . '/allowed-params', 'none');
    }

    public function classes(): mixed
    {
        return $this->t->get('/v1/playground/model-classes', 'none');
    }
}
