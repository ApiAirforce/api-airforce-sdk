<?php

declare(strict_types=1);

namespace Airforce;

final class Multipart
{
    /**
     * @param array<string,string> $fields
     * @param list<array{field:string,filename:string,data:string}> $files
     * @return array{body:string, contentType:string}
     */
    public static function build(array $fields, array $files): array
    {
        $boundary = 'airforceBoundary' . bin2hex(random_bytes(12));
        $body = '';
        foreach ($fields as $name => $value) {
            $body .= "--{$boundary}\r\nContent-Disposition: form-data; name=\"{$name}\"\r\n\r\n{$value}\r\n";
        }
        foreach ($files as $file) {
            $body .= "--{$boundary}\r\nContent-Disposition: form-data; name=\"{$file['field']}\"; "
                . "filename=\"{$file['filename']}\"\r\nContent-Type: application/octet-stream\r\n\r\n";
            $body .= $file['data'] . "\r\n";
        }
        $body .= "--{$boundary}--\r\n";

        return ['body' => $body, 'contentType' => "multipart/form-data; boundary={$boundary}"];
    }
}
