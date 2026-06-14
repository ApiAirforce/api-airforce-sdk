<?php

declare(strict_types=1);

namespace Airforce\Resources;

use Airforce\AirforceException;
use Airforce\Transport;

/** Async video generation — /v1/video/*. */
final class Video
{
    private const TERMINAL = ['completed', 'failed', 'expired'];

    public function __construct(private Transport $t)
    {
    }

    /** @param array<string,mixed> $request */
    public function generate(array $request): mixed
    {
        return $this->t->post('/v1/video/generations', 'api_key', $request);
    }

    public function getTask(string $id): mixed
    {
        return $this->t->get('/v1/video/tasks/' . rawurlencode($id), 'api_key');
    }

    public function listTasks(): mixed
    {
        $res = $this->t->get('/v1/video/tasks', 'api_key');
        return is_array($res) && isset($res['data']) ? $res['data'] : $res;
    }

    public function deleteTask(string $id): mixed
    {
        return $this->t->delete('/v1/video/tasks/' . rawurlencode($id), 'api_key');
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
                throw new AirforceException("video task {$id} ended with status {$status}", code: $status);
            }
            if (microtime(true) > $deadline) {
                throw new AirforceException("timed out waiting for video task {$id}", code: 'wait_timeout');
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
            throw new AirforceException('video task response had no task_id');
        }
        return $this->waitForCompletion($id, $pollSeconds, $timeoutSeconds);
    }
}
