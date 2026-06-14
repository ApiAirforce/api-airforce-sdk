<?php

declare(strict_types=1);

namespace Airforce\Resources;

use Airforce\Multipart;
use Airforce\Transport;

/** Audio — TTS, music, SFX, transcription, dubbing, voices (/v1/audio/*). */
final class Audio
{
    public function __construct(private Transport $t)
    {
    }

    /** @param array<string,mixed> $request */
    public function speech(array $request): string
    {
        return $this->t->postBytes('/v1/audio/speech', 'api_key', $request);
    }

    /** @param array<string,mixed> $request */
    public function music(array $request): string
    {
        return $this->t->postBytes('/v1/audio/music', 'api_key', $request);
    }

    /** @param array<string,mixed> $request */
    public function soundEffects(array $request): string
    {
        return $this->t->postBytes('/v1/audio/sound-effects', 'api_key', $request);
    }

    /** @param array<string,string> $extra */
    public function transcriptions(string $model, string $file, string $filename, array $extra = []): mixed
    {
        $m = Multipart::build(['model' => $model] + $extra, [['field' => 'file', 'filename' => $filename, 'data' => $file]]);
        return $this->t->multipart('/v1/audio/transcriptions', $m['body'], $m['contentType']);
    }

    public function audioIsolation(string $model, string $file, string $filename, ?string $output = null): string
    {
        $fields = ['model' => $model];
        if ($output !== null) {
            $fields['output'] = $output;
        }
        $m = Multipart::build($fields, [['field' => 'file', 'filename' => $filename, 'data' => $file]]);
        return $this->t->multipart('/v1/audio/audio-isolation', $m['body'], $m['contentType'], true);
    }

    public function voiceChanger(string $model, string $file, string $filename, string $voice): string
    {
        $m = Multipart::build(['model' => $model, 'voice' => $voice], [['field' => 'file', 'filename' => $filename, 'data' => $file]]);
        return $this->t->multipart('/v1/audio/voice-changer', $m['body'], $m['contentType'], true);
    }

    /** @param array<string,string> $extra */
    public function dubbing(string $model, string $file, string $filename, string $targetLang, array $extra = []): mixed
    {
        $fields = ['model' => $model, 'target_lang' => $targetLang] + $extra;
        $m = Multipart::build($fields, [['field' => 'file', 'filename' => $filename, 'data' => $file]]);
        return $this->t->multipart('/v1/audio/dubbing', $m['body'], $m['contentType']);
    }

    public function dubbingStatus(string $id): mixed
    {
        return $this->t->get('/v1/audio/dubbing/' . rawurlencode($id), 'api_key');
    }

    public function dubbingAudio(string $id, string $lang): string
    {
        return $this->t->getBytes('/v1/audio/dubbing/' . rawurlencode($id) . '/audio/' . rawurlencode($lang), 'api_key');
    }

    public function voices(): mixed
    {
        $res = $this->t->get('/v1/audio/voices', 'api_key');
        return is_array($res) && isset($res['voices']) ? $res['voices'] : $res;
    }
}
