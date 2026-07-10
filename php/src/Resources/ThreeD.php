<?php

declare(strict_types=1);

namespace Airforce\Resources;

use Airforce\AirforceException;
use Airforce\Transport;

/** Async 3D generation — /v1/3d/*. Tasks and their artifacts expire after 24 h. */
final class ThreeD
{
    private const TERMINAL = ['completed', 'failed', 'expired'];

    public function __construct(private Transport $t)
    {
    }

    /**
     * Create a 3D generation task. Credits are deducted only when the worker picks up
     * the task; failures are refunded.
     *
     * @param array<string,mixed> $request `{model, image_urls?: string[] (http(s) URL or data: URI, ≤4), resolution?: 'low'|'medium'|'high', prompt?, ...extra}`
     */
    public function generate(array $request): mixed
    {
        return $this->t->post('/v1/3d/generations', 'api_key', $request);
    }

    public function getTask(string $id): mixed
    {
        return $this->t->get('/v1/3d/tasks/' . rawurlencode($id), 'api_key');
    }

    public function listTasks(): mixed
    {
        $res = $this->t->get('/v1/3d/tasks', 'api_key');
        return is_array($res) && isset($res['data']) ? $res['data'] : $res;
    }

    public function deleteTask(string $id): mixed
    {
        return $this->t->delete('/v1/3d/tasks/' . rawurlencode($id), 'api_key');
    }

    /** Download the finished model artifact (glb/ply bytes); 404 until `has_result`. */
    public function content(string $id): string
    {
        return $this->t->getBytes('/v1/3d/tasks/' . rawurlencode($id) . '/content', 'api_key');
    }

    /** Poll a task until it reaches a terminal state. */
    public function waitForCompletion(string $id, float $pollSeconds = 2.5, float $timeoutSeconds = 600.0): mixed
    {
        $deadline = microtime(true) + $timeoutSeconds;
        while (true) {
            $task = $this->getTask($id);
            $status = is_array($task) ? ($task['status'] ?? '') : '';
            if ($status === 'completed') {
                return $task;
            }
            if (in_array($status, self::TERMINAL, true)) {
                throw new AirforceException("3d task {$id} ended with status {$status}", code: $status);
            }
            if (microtime(true) > $deadline) {
                throw new AirforceException("timed out waiting for 3d task {$id}", code: 'wait_timeout');
            }
            usleep((int) ($pollSeconds * 1_000_000));
        }
    }

    /** @param array<string,mixed> $request */
    public function generateAndWait(array $request, float $pollSeconds = 2.5, float $timeoutSeconds = 600.0): mixed
    {
        $task = $this->generate($request);
        $id = is_array($task) ? ($task['task_id'] ?? null) : null;
        if ($id === null) {
            throw new AirforceException('3d task response had no task_id');
        }
        return $this->waitForCompletion($id, $pollSeconds, $timeoutSeconds);
    }
}
