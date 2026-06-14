<?php

declare(strict_types=1);

namespace Airforce\Resources;

use Airforce\Transport;

/** OAuth 2.0 provider flow + self-service app management. */
final class OAuth
{
    public function __construct(private Transport $t)
    {
    }

    /**
     * Generate a PKCE verifier/challenge pair (S256).
     *
     * @return array{verifier:string, challenge:string, method:string}
     */
    public static function createPkcePair(): array
    {
        $verifier = self::base64Url(random_bytes(32));
        $challenge = self::base64Url(hash('sha256', $verifier, true));
        return ['verifier' => $verifier, 'challenge' => $challenge, 'method' => 'S256'];
    }

    /** @param list<string>|null $scope */
    public function authorizeUrl(
        string $clientId,
        string $redirectUri,
        ?array $scope = null,
        ?string $state = null,
        ?string $codeChallenge = null,
        string $codeChallengeMethod = 'S256',
    ): string {
        $query = [
            'response_type' => 'code',
            'client_id' => $clientId,
            'redirect_uri' => $redirectUri,
        ];
        if ($scope !== null && $scope !== []) {
            $query['scope'] = implode(' ', $scope);
        }
        if ($state !== null) {
            $query['state'] = $state;
        }
        if ($codeChallenge !== null) {
            $query['code_challenge'] = $codeChallenge;
            $query['code_challenge_method'] = $codeChallengeMethod;
        }
        return $this->t->baseUrl . '/oauth/authorize?' . http_build_query($query);
    }

    /** @param array<string,string> $params */
    public function exchangeToken(array $params): mixed
    {
        return $this->t->form('/oauth/token', ['grant_type' => 'authorization_code'] + $params);
    }

    public function userInfo(string $accessToken): mixed
    {
        return $this->t->getWithHeader('/oauth/userinfo', ['authorization' => 'Bearer ' . $accessToken]);
    }

    public function revokeToken(string $token): mixed
    {
        return $this->t->form('/oauth/revoke', ['token' => $token]);
    }

    public function listApps(): mixed
    {
        return $this->t->get('/api/me/oauth-apps', 'session');
    }
    /** @param array<string,mixed> $request */
    public function createApp(array $request): mixed
    {
        return $this->t->post('/api/me/oauth-apps', 'session', $request);
    }
    public function getApp(string $clientId): mixed
    {
        return $this->t->get('/api/me/oauth-apps/' . rawurlencode($clientId), 'session');
    }
    /** @param array<string,mixed> $patch */
    public function updateApp(string $clientId, array $patch): mixed
    {
        return $this->t->method('PATCH', '/api/me/oauth-apps/' . rawurlencode($clientId), 'session', $patch);
    }
    public function deleteApp(string $clientId): mixed
    {
        return $this->t->delete('/api/me/oauth-apps/' . rawurlencode($clientId), 'session');
    }
    public function rotateSecret(string $clientId): mixed
    {
        return $this->t->post('/api/me/oauth-apps/' . rawurlencode($clientId) . '/rotate-secret', 'session');
    }
    public function connectedApps(): mixed
    {
        return $this->t->get('/api/me/connected-apps', 'session');
    }
    public function revokeConnectedApp(string $clientId): mixed
    {
        return $this->t->delete('/api/me/connected-apps/' . rawurlencode($clientId), 'session');
    }

    private static function base64Url(string $bytes): string
    {
        return rtrim(strtr(base64_encode($bytes), '+/', '-_'), '=');
    }
}
