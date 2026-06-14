<?php

declare(strict_types=1);

namespace Airforce\Resources;

use Airforce\Transport;

/** Authentication — /auth/*. Login/signup adopt the session token automatically. */
final class Auth
{
    public function __construct(private Transport $t)
    {
    }

    /**
     * @param array<string,mixed>|null $body
     * @param array<string,string>|null $headers
     */
    private function submit(string $path, ?array $body, ?array $headers = null): mixed
    {
        [$json, $cookie] = $this->t->requestJsonCookie($path, $body, $headers);
        if ($cookie !== null) {
            $this->t->setSessionToken($cookie);
            if (is_array($json)) {
                $json['session_token'] = $cookie;
            }
        }
        return $json;
    }

    /** @param array<string,mixed> $request */
    public function signup(array $request): mixed
    {
        return $this->submit('/auth/signup', $request);
    }

    /** @param array<string,mixed> $request */
    public function signupPrecheck(array $request): mixed
    {
        return $this->t->post('/auth/signup/precheck', 'none', $request);
    }

    public function login(string $username, string $password, string $captchaToken): mixed
    {
        return $this->submit('/auth/login', [
            'username' => $username,
            'password' => $password,
            'captcha_token' => $captchaToken,
        ]);
    }

    public function verify2fa(string $challengeToken, string $code, ?string $backupCode = null): mixed
    {
        $body = ['code' => $code];
        if ($backupCode !== null) {
            $body['backup_code'] = $backupCode;
        }
        return $this->submit('/auth/2fa/verify', $body, ['authorization' => 'Bearer ' . $challengeToken]);
    }

    public function verifyEmail(string $token): mixed
    {
        return $this->t->post('/auth/verify', 'none', ['token' => $token]);
    }

    public function resendVerification(string $identifier): mixed
    {
        return $this->t->post('/auth/resend-verification', 'none', ['identifier' => $identifier]);
    }

    public function logout(): mixed
    {
        $result = $this->t->post('/auth/logout', 'session');
        $this->t->setSessionToken(null);
        return $result;
    }
}
