<?php

declare(strict_types=1);

namespace Airforce;

use Airforce\Resources\Account;
use Airforce\Resources\Audio;
use Airforce\Resources\Auth;
use Airforce\Resources\Billing;
use Airforce\Resources\Chat;
use Airforce\Resources\Gemini;
use Airforce\Resources\Images;
use Airforce\Resources\Keys;
use Airforce\Resources\Messages;
use Airforce\Resources\Models;
use Airforce\Resources\OAuth;
use Airforce\Resources\Responses;
use Airforce\Resources\TwoFactor;
use Airforce\Resources\Video;
use Airforce\Resources\Voices;

/**
 * The api.airforce API client.
 *
 * ```php
 * $client = new Airforce\Client(apiKey: 'sk-air-...');
 * $res = $client->chat->create([
 *     'model' => 'claude-opus-4.8',
 *     'messages' => [['role' => 'user', 'content' => 'Hello!']],
 * ]);
 * ```
 */
final class Client
{
    private Transport $transport;

    public readonly Chat $chat;
    public readonly Messages $messages;
    public readonly Responses $responses;
    public readonly Gemini $gemini;
    public readonly Models $models;
    public readonly Images $images;
    public readonly Audio $audio;
    public readonly Video $video;
    public readonly Voices $voices;
    public readonly Account $account;
    public readonly Keys $keys;
    public readonly Billing $billing;
    public readonly TwoFactor $twofa;
    public readonly Auth $auth;
    public readonly OAuth $oauth;

    /** @param array<string,string> $defaultHeaders */
    public function __construct(
        ?string $apiKey = null,
        ?string $sessionToken = null,
        ?string $baseUrl = null,
        float $timeout = 60.0,
        int $maxRetries = 2,
        array $defaultHeaders = [],
        ?HttpSender $sender = null,
    ) {
        $apiKey ??= getenv('AIRFORCE_API_KEY') ?: null;
        $sessionToken ??= getenv('AIRFORCE_SESSION_TOKEN') ?: null;
        $baseUrl ??= getenv('AIRFORCE_BASE_URL') ?: 'https://api.airforce';

        $this->transport = new Transport(
            $sender ?? new CurlSender($timeout),
            $apiKey,
            $sessionToken,
            rtrim($baseUrl, '/'),
            $maxRetries,
            $defaultHeaders,
        );

        $this->chat = new Chat($this->transport);
        $this->messages = new Messages($this->transport);
        $this->responses = new Responses($this->transport);
        $this->gemini = new Gemini($this->transport);
        $this->models = new Models($this->transport);
        $this->images = new Images($this->transport);
        $this->audio = new Audio($this->transport);
        $this->video = new Video($this->transport);
        $this->voices = new Voices($this->transport);
        $this->account = new Account($this->transport);
        $this->keys = new Keys($this->transport);
        $this->billing = new Billing($this->transport);
        $this->twofa = new TwoFactor($this->transport);
        $this->auth = new Auth($this->transport);
        $this->oauth = new OAuth($this->transport);
    }

    public function baseUrl(): string
    {
        return $this->transport->baseUrl;
    }

    public function setSessionToken(?string $token): void
    {
        $this->transport->setSessionToken($token);
    }
}
