package com.airforce;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.io.InputStream;
import java.net.URI;
import java.net.URLEncoder;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.net.http.HttpTimeoutException;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ThreadLocalRandom;

class Transport {

  static final String VERSION = "0.0.1";
  // 409 is excluded: a terminal business conflict (e.g. "already subscribed"), not transient.
  private static final Set<Integer> RETRYABLE = Set.of(408, 429, 500, 502, 503, 504);

  private final HttpClient http;
  private final ObjectMapper mapper = new ObjectMapper();
  private final String baseUrl;
  private final int maxRetries;
  private final Duration timeout;
  private final Map<String, String> defaultHeaders;

  private String apiKey;
  private String sessionToken;

  Transport(HttpClient http, String apiKey, String sessionToken, String baseUrl,
      Duration timeout, int maxRetries, Map<String, String> defaultHeaders) {
    this.http = http;
    this.apiKey = apiKey;
    this.sessionToken = sessionToken;
    this.baseUrl = baseUrl;
    this.timeout = timeout;
    this.maxRetries = maxRetries;
    this.defaultHeaders = defaultHeaders;
  }

  ObjectMapper mapper() {
    return mapper;
  }

  void setSessionToken(String token) {
    this.sessionToken = token;
  }

  String sessionToken() {
    return sessionToken;
  }

  String baseUrl() {
    return baseUrl;
  }

  // --- request spec --------------------------------------------------------

  static class RequestSpec {
    String auth = "api_key";
    Map<String, String> query;
    Object jsonBody;
    byte[] rawBody;
    String contentType;
    Map<String, String> headers;
  }

  // --- public entry points -------------------------------------------------

  JsonNode requestJson(String method, String path, RequestSpec spec) {
    HttpResponse<InputStream> resp = send(method, path, spec, false);
    try (InputStream in = resp.body()) {
      byte[] bytes = in.readAllBytes();
      if (resp.statusCode() == 204 || bytes.length == 0) {
        return mapper.nullNode();
      }
      return mapper.readTree(bytes);
    } catch (IOException e) {
      throw new AirforceException.ApiConnection("airforce: failed reading response", e);
    }
  }

  /** Holder for a JSON response plus the airforce_session cookie (auth flow). */
  static class JsonAndCookie {
    final JsonNode json;
    final String sessionCookie;

    JsonAndCookie(JsonNode json, String sessionCookie) {
      this.json = json;
      this.sessionCookie = sessionCookie;
    }
  }

  JsonAndCookie requestJsonCookie(String method, String path, RequestSpec spec) {
    HttpResponse<InputStream> resp = send(method, path, spec, false);
    JsonNode json;
    try (InputStream in = resp.body()) {
      byte[] bytes = in.readAllBytes();
      json = bytes.length == 0 ? mapper.nullNode() : mapper.readTree(bytes);
    } catch (IOException e) {
      throw new AirforceException.ApiConnection("airforce: failed reading response", e);
    }
    String cookie = null;
    for (String header : resp.headers().allValues("set-cookie")) {
      int idx = header.indexOf("airforce_session=");
      if (idx >= 0) {
        String rest = header.substring(idx + "airforce_session=".length());
        int semi = rest.indexOf(';');
        cookie = semi >= 0 ? rest.substring(0, semi) : rest;
        break;
      }
    }
    return new JsonAndCookie(json, cookie);
  }

  byte[] requestBytes(String method, String path, RequestSpec spec) {
    HttpResponse<InputStream> resp = send(method, path, spec, false);
    try (InputStream in = resp.body()) {
      return in.readAllBytes();
    } catch (IOException e) {
      throw new AirforceException.ApiConnection("airforce: failed reading response", e);
    }
  }

  Stream requestStream(String method, String path, RequestSpec spec) {
    HttpResponse<InputStream> resp = send(method, path, spec, true);
    return new Stream(resp.body(), mapper);
  }

  // convenience wrappers used by resources

  JsonNode method(String method, String path, String auth, Object body) {
    RequestSpec spec = new RequestSpec();
    spec.auth = auth;
    spec.jsonBody = body;
    return requestJson(method, path, spec);
  }

  JsonNode post(String path, String auth, Object body) {
    return method("POST", path, auth, body);
  }

  JsonNode get(String path, String auth, Map<String, String> query) {
    RequestSpec spec = new RequestSpec();
    spec.auth = auth;
    spec.query = query;
    return requestJson("GET", path, spec);
  }

  JsonNode delete(String path, String auth) {
    RequestSpec spec = new RequestSpec();
    spec.auth = auth;
    return requestJson("DELETE", path, spec);
  }

  byte[] postBytes(String path, String auth, Object body) {
    RequestSpec spec = new RequestSpec();
    spec.auth = auth;
    spec.jsonBody = body;
    return requestBytes("POST", path, spec);
  }

  byte[] getBytes(String path, String auth) {
    RequestSpec spec = new RequestSpec();
    spec.auth = auth;
    return requestBytes("GET", path, spec);
  }

  Stream postStream(String path, String auth, Object body) {
    RequestSpec spec = new RequestSpec();
    spec.auth = auth;
    spec.jsonBody = body;
    return requestStream("POST", path, spec);
  }

  // --- internals -----------------------------------------------------------

  private String resolveToken(String auth) {
    if ("none".equals(auth)) {
      return null;
    }
    // Session endpoints require a session JWT — never substitute an API key.
    String token = "session".equals(auth)
        ? sessionToken
        : firstNonEmpty(apiKey, sessionToken);
    if (token == null) {
      throw new AirforceException.MissingCredential(
          "session".equals(auth)
              ? "This endpoint requires a session token (set sessionToken / auth().login())."
              : "This endpoint requires an API key (set apiKey).");
    }
    return token;
  }

  private byte[] bodyBytes(RequestSpec spec) {
    if (spec.rawBody != null) {
      return spec.rawBody;
    }
    if (spec.jsonBody != null) {
      try {
        return mapper.writeValueAsBytes(spec.jsonBody);
      } catch (IOException e) {
        throw new AirforceException("airforce: failed to encode request body", 0, null, null, null, 0, null, e);
      }
    }
    return null;
  }

  private HttpRequest buildRequest(String method, String url, RequestSpec spec, String token,
      String contentType, byte[] body, boolean stream) {
    HttpRequest.BodyPublisher publisher = body != null
        ? HttpRequest.BodyPublishers.ofByteArray(body)
        : HttpRequest.BodyPublishers.noBody();
    HttpRequest.Builder b = HttpRequest.newBuilder(URI.create(url))
        .timeout(timeout)
        .method(method, publisher)
        .header("user-agent", "airforce-sdk-java/" + VERSION)
        .header("x-airforce-sdk", "java/" + VERSION)
        .header("accept", stream ? "text/event-stream" : "application/json");
    if (contentType != null) {
      b.header("content-type", contentType);
    }
    if (token != null) {
      b.header("authorization", "Bearer " + token);
    }
    defaultHeaders.forEach(b::header);
    if (spec.headers != null) {
      spec.headers.forEach(b::header);
    }
    return b.build();
  }

  private HttpResponse<InputStream> send(String method, String path, RequestSpec spec, boolean stream) {
    String url = buildUrl(path, spec.query);
    String token = resolveToken(spec.auth);
    byte[] body = bodyBytes(spec);
    String contentType = spec.contentType != null
        ? spec.contentType
        : (spec.jsonBody != null ? "application/json" : null);

    for (int attempt = 0; ; attempt++) {
      HttpRequest request = buildRequest(method, url, spec, token, contentType, body, stream);
      HttpResponse<InputStream> resp = attempt(request, path, attempt);
      if (resp == null) {
        continue; // a retry was scheduled
      }
      int code = resp.statusCode();
      if (code < 400) {
        return resp;
      }
      if (RETRYABLE.contains(code) && attempt < maxRetries) {
        double retryAfter = retryAfterSeconds(resp);
        drain(resp);
        sleep(backoffMillis(attempt + 1, retryAfter));
        continue;
      }
      throw AirforceException.fromResponse(code, readBody(resp),
          resp.headers().firstValue("x-request-id").orElse(null), retryAfterSeconds(resp));
    }
  }

  /** One HTTP attempt; returns null (after scheduling a retry) or throws on terminal failure. */
  private HttpResponse<InputStream> attempt(HttpRequest request, String path, int attempt) {
    // A transport error leaves a POST's outcome unknown — retrying could double-charge a
    // billable request. Only retry idempotent methods.
    boolean idempotent = !"POST".equalsIgnoreCase(request.method());
    try {
      return http.send(request, HttpResponse.BodyHandlers.ofInputStream());
    } catch (HttpTimeoutException e) {
      if (attempt < maxRetries && idempotent) {
        sleep(backoffMillis(attempt + 1, 0));
        return null;
      }
      throw new AirforceException.ApiTimeout("airforce: request to " + path + " timed out", e);
    } catch (IOException e) {
      if (attempt < maxRetries && idempotent) {
        sleep(backoffMillis(attempt + 1, 0));
        return null;
      }
      throw new AirforceException.ApiConnection("airforce: request to " + path + " failed: " + e.getMessage(), e);
    } catch (InterruptedException e) {
      Thread.currentThread().interrupt();
      throw new AirforceException.ApiConnection("airforce: request interrupted", e);
    }
  }

  private String buildUrl(String path, Map<String, String> query) {
    StringBuilder url = new StringBuilder(baseUrl);
    url.append(path.startsWith("/") ? path : "/" + path);
    if (query != null && !query.isEmpty()) {
      StringBuilder qs = new StringBuilder();
      for (Map.Entry<String, String> e : query.entrySet()) {
        if (e.getValue() == null) {
          continue;
        }
        qs.append(qs.length() == 0 ? '?' : '&')
            .append(URLEncoder.encode(e.getKey(), StandardCharsets.UTF_8))
            .append('=')
            .append(URLEncoder.encode(e.getValue(), StandardCharsets.UTF_8));
      }
      url.append(qs);
    }
    return url.toString();
  }

  private static String firstNonEmpty(String a, String b) {
    if (a != null && !a.isEmpty()) {
      return a;
    }
    return (b != null && !b.isEmpty()) ? b : null;
  }

  private static double retryAfterSeconds(HttpResponse<?> resp) {
    return resp.headers().firstValue("retry-after").map(v -> {
      try {
        return Double.parseDouble(v);
      } catch (NumberFormatException e) {
        return 0.0;
      }
    }).orElse(0.0);
  }

  private static long backoffMillis(int attempt, double retryAfterSeconds) {
    double base = retryAfterSeconds > 0 ? retryAfterSeconds : Math.min(Math.pow(2, attempt - 1), 8);
    double jitter = base * 0.25 * ThreadLocalRandom.current().nextDouble();
    return (long) ((base + jitter) * 1000);
  }

  private static void sleep(long millis) {
    try {
      Thread.sleep(millis);
    } catch (InterruptedException e) {
      Thread.currentThread().interrupt();
      throw new AirforceException.ApiConnection("airforce: retry sleep interrupted", e);
    }
  }

  private static void drain(HttpResponse<InputStream> resp) {
    try (InputStream in = resp.body()) {
      in.readAllBytes();
    } catch (IOException ignored) {
      // best effort
    }
  }

  private static String readBody(HttpResponse<InputStream> resp) {
    try (InputStream in = resp.body()) {
      return new String(in.readAllBytes(), StandardCharsets.UTF_8);
    } catch (IOException e) {
      return "";
    }
  }
}
