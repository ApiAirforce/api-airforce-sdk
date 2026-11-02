<?php

declare(strict_types=1);

namespace Airforce\Resources;

use Airforce\Multipart;
use Airforce\Transport;

/** Image generation — POST /v1/images/generations — and edits — POST /v1/images/edits. */
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

    /**
     * Edit or vary input image(s) (multipart). Each entry of $images becomes one `image` part: at
     * least one, at most 16, 25 MB each. $extra carries optional form fields (n, size,
     * aspect_ratio, quality, response_format). Same models, prices and response shape as generate().
     *
     * @param list<array{filename:string,data:string}> $images
     * @param array{filename:string,data:string}|null $mask
     * @param array<string,string> $extra
     */
    public function edit(string $model, string $prompt, array $images, ?array $mask = null, array $extra = []): mixed
    {
        $files = [];
        foreach ($images as $image) {
            $files[] = ['field' => 'image', 'filename' => $image['filename'], 'data' => $image['data']];
        }
        if ($mask !== null) {
            $files[] = ['field' => 'mask', 'filename' => $mask['filename'], 'data' => $mask['data']];
        }
        $m = Multipart::build(['model' => $model, 'prompt' => $prompt] + $extra, $files);
        return $this->t->multipart('/v1/images/edits', $m['body'], $m['contentType']);
    }
}
