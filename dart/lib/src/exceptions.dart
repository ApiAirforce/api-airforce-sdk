import 'dart:convert';

/// Base exception for all SDK failures.
class AirforceException implements Exception {
  final int status;
  final String? code;
  final String? type;
  final String message;
  final String? requestId;

  /// Seconds to wait before retrying, for 429 responses (0 if absent).
  final double retryAfter;
  final String? body;

  AirforceException(
    this.message, {
    this.status = 0,
    this.code,
    this.type,
    this.requestId,
    this.retryAfter = 0,
    this.body,
  });

  bool get isBadRequest => status == 400;
  bool get isAuthentication => status == 401;
  bool get isInsufficientBalance => status == 402;
  bool get isPermissionDenied => status == 403;
  bool get isNotFound => status == 404;
  bool get isConflict => status == 409;
  bool get isRateLimited => status == 429;
  bool get isServerError => status >= 500;

  @override
  String toString() => code != null
      ? 'AirforceException(HTTP $status): $message ($code)'
      : 'AirforceException(HTTP $status): $message';

  factory AirforceException.fromResponse(
      int status, String? body, String? requestId, double retryAfter) {
    String? message, code, type;
    if (body != null && body.isNotEmpty) {
      try {
        final root = jsonDecode(body);
        if (root is Map) {
          final err = root['error'];
          if (err is Map) {
            message = err['message'] as String?;
            code = err['code'] as String?;
            type = err['type'] as String?;
          } else if (err is String) {
            message = err;
          } else {
            message = root['message'] as String?;
            code = root['code'] as String?;
            type = root['type'] as String?;
          }
        }
      } on FormatException {
        // non-JSON body — fall through to a generic message
      }
    }
    return AirforceException(
      message ?? 'Airforce API error (HTTP $status)',
      status: status,
      code: code,
      type: type,
      requestId: requestId,
      retryAfter: retryAfter,
      body: body,
    );
  }
}

/// A required credential (API key or session token) was not configured.
class MissingCredentialException extends AirforceException {
  MissingCredentialException(super.message);
}

/// No HTTP response was received (DNS, TCP, TLS, transport failure).
class ApiConnectionException extends AirforceException {
  ApiConnectionException(super.message);
}

/// The request exceeded the configured timeout.
class ApiTimeoutException extends AirforceException {
  ApiTimeoutException(super.message);
}
