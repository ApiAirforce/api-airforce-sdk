package com.airforce;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

/**
 * Base exception for all SDK failures. HTTP errors carry the response {@link #status()};
 * use the {@code is*} helpers or compare the status directly. Transport-level failures are
 * raised as {@link ApiConnection} / {@link ApiTimeout}; a missing credential as
 * {@link MissingCredential}.
 */
public class AirforceException extends RuntimeException {

  private static final ObjectMapper MAPPER = new ObjectMapper();

  private final int status;
  private final String code;
  private final String type;
  private final String requestId;
  private final double retryAfter;
  private final String body;

  public AirforceException(String message) {
    this(message, 0, null, null, null, 0, null, null);
  }

  public AirforceException(
      String message,
      int status,
      String code,
      String type,
      String requestId,
      double retryAfter,
      String body,
      Throwable cause) {
    super(message, cause);
    this.status = status;
    this.code = code;
    this.type = type;
    this.requestId = requestId;
    this.retryAfter = retryAfter;
    this.body = body;
  }

  public int status() {
    return status;
  }

  public String code() {
    return code;
  }

  public String type() {
    return type;
  }

  public String requestId() {
    return requestId;
  }

  /** Seconds to wait before retrying, for 429 responses (0 if not provided). */
  public double retryAfter() {
    return retryAfter;
  }

  public String body() {
    return body;
  }

  public boolean isBadRequest() {
    return status == 400;
  }

  public boolean isAuthentication() {
    return status == 401;
  }

  public boolean isInsufficientBalance() {
    return status == 402;
  }

  public boolean isPermissionDenied() {
    return status == 403;
  }

  public boolean isNotFound() {
    return status == 404;
  }

  public boolean isConflict() {
    return status == 409;
  }

  public boolean isRateLimited() {
    return status == 429;
  }

  public boolean isServerError() {
    return status >= 500;
  }

  static AirforceException fromResponse(int status, String body, String requestId, double retryAfter) {
    String message = null;
    String code = null;
    String type = null;
    try {
      JsonNode root = MAPPER.readTree(body);
      JsonNode err = root.get("error");
      if (err != null && err.isObject()) {
        message = text(err, "message");
        code = text(err, "code");
        type = text(err, "type");
      } else if (err != null && err.isTextual()) {
        message = err.asText();
      } else {
        message = text(root, "message");
        code = text(root, "code");
        type = text(root, "type");
      }
    } catch (Exception ignored) {
      // non-JSON body — fall through to a generic message
    }
    if (message == null || message.isEmpty()) {
      message = "Airforce API error (HTTP " + status + ")";
    }
    return new AirforceException(message, status, code, type, requestId, retryAfter, body, null);
  }

  private static String text(JsonNode node, String field) {
    JsonNode value = node.get(field);
    return value != null && value.isTextual() ? value.asText() : null;
  }

  /** A required credential (API key or session token) was not configured. */
  public static class MissingCredential extends AirforceException {
    public MissingCredential(String message) {
      super(message);
    }
  }

  /** No HTTP response was received (DNS, TCP, TLS, transport failure). */
  public static class ApiConnection extends AirforceException {
    public ApiConnection(String message, Throwable cause) {
      super(message, 0, null, null, null, 0, null, cause);
    }
  }

  /** The request exceeded the configured timeout. */
  public static class ApiTimeout extends AirforceException {
    public ApiTimeout(String message, Throwable cause) {
      super(message, 0, null, null, null, 0, null, cause);
    }
  }
}
