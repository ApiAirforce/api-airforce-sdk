<?php

declare(strict_types=1);

namespace Airforce;

/**
 * Base exception for all SDK failures.
 */
class AirforceException extends \Exception
{
    public int $status;
    public ?string $errorCode;
    public ?string $type;
    public ?string $requestId;

    /** Seconds to wait before retrying, for 429 responses (0 if absent). */
    public float $retryAfter;
    public ?string $body;

    public function __construct(
        string $message,
        int $status = 0,
        ?string $code = null,
        ?string $type = null,
        ?string $requestId = null,
        float $retryAfter = 0.0,
        ?string $body = null
    ) {
        parent::__construct($message);
        $this->status = $status;
        $this->errorCode = $code;
        $this->type = $type;
        $this->requestId = $requestId;
        $this->retryAfter = $retryAfter;
        $this->body = $body;
    }

    /** Machine-readable error code (e.g. `free_tier_gated`), if provided. */
    public function code(): ?string
    {
        return $this->errorCode;
    }

    public function isBadRequest(): bool
    {
        return $this->status === 400;
    }
    public function isAuthentication(): bool
    {
        return $this->status === 401;
    }
    public function isInsufficientBalance(): bool
    {
        return $this->status === 402;
    }
    public function isPermissionDenied(): bool
    {
        return $this->status === 403;
    }
    public function isNotFound(): bool
    {
        return $this->status === 404;
    }
    public function isConflict(): bool
    {
        return $this->status === 409;
    }
    public function isRateLimited(): bool
    {
        return $this->status === 429;
    }
    public function isServerError(): bool
    {
        return $this->status >= 500;
    }

    public static function fromResponse(int $status, ?string $body, ?string $requestId, float $retryAfter): self
    {
        $message = null;
        $code = null;
        $type = null;
        if ($body !== null && $body !== '') {
            $root = json_decode($body, true);
            if (is_array($root)) {
                $err = $root['error'] ?? null;
                if (is_array($err)) {
                    $message = $err['message'] ?? null;
                    $code = $err['code'] ?? null;
                    $type = $err['type'] ?? null;
                } elseif (is_string($err)) {
                    $message = $err;
                } else {
                    $message = $root['message'] ?? null;
                    $code = $root['code'] ?? null;
                    $type = $root['type'] ?? null;
                }
            }
        }
        return new self(
            $message ?? "Airforce API error (HTTP {$status})",
            $status,
            $code,
            $type,
            $requestId,
            $retryAfter,
            $body
        );
    }
}
