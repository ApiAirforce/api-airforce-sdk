<?php

declare(strict_types=1);

namespace Airforce\Resources;

use Airforce\Multipart;
use Airforce\Transport;

/** Voice cloning — /v1/voices/*. */
final class Voices
{
    public function __construct(private Transport $t)
    {
    }

    public function consentText(): mixed
    {
        return $this->t->get('/v1/voices/consent-text', 'none');
    }

    /**
     * Create a cloned voice from one or more samples.
     *
     * @param list<array{filename:string,data:string}> $samples
     * @param array<string,string> $extra
     */
    public function clone(string $name, string $consentHash, array $samples, array $extra = []): mixed
    {
        $fields = ['name' => $name, 'consent_hash' => $consentHash] + $extra;
        $files = array_map(
            static fn (array $s): array => ['field' => 'files', 'filename' => $s['filename'], 'data' => $s['data']],
            $samples
        );
        $m = Multipart::build($fields, $files);
        return $this->t->multipart('/v1/voices/clone', $m['body'], $m['contentType']);
    }

    public function library(): mixed
    {
        $res = $this->t->get('/v1/voices/library', 'api_key');
        return is_array($res) && isset($res['voices']) ? $res['voices'] : $res;
    }

    /** @param array<string,mixed> $body */
    public function update(string $voiceId, array $body): mixed
    {
        return $this->t->method('PATCH', '/v1/voices/clone/' . rawurlencode($voiceId), 'api_key', $body);
    }

    public function delete(string $voiceId): mixed
    {
        return $this->t->delete('/v1/voices/clone/' . rawurlencode($voiceId), 'api_key');
    }
}
