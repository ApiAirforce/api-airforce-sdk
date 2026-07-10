package com.airforce;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.fasterxml.jackson.databind.JsonNode;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpHandler;
import com.sun.net.httpserver.HttpServer;
import java.io.IOException;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicReference;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;

class AirforceTest {

  private static final String COMPLETION =
      "{\"id\":\"cmpl_1\",\"object\":\"chat.completion\",\"created\":0,\"model\":\"claude-opus-4.8\","
          + "\"choices\":[{\"index\":0,\"message\":{\"role\":\"assistant\",\"content\":\"hi\"},\"finish_reason\":\"stop\"}]}";

  private HttpServer server;

  @AfterEach
  void stop() {
    if (server != null) {
      server.stop(0);
    }
  }

  private Airforce start(HttpHandler handler) throws IOException {
    server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
    server.createContext("/", handler);
    server.start();
    String base = "http://127.0.0.1:" + server.getAddress().getPort();
    return Airforce.builder().apiKey("sk-air-test").baseUrl(base).build();
  }

  private Airforce startSession(HttpHandler handler) throws IOException {
    server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
    server.createContext("/", handler);
    server.start();
    String base = "http://127.0.0.1:" + server.getAddress().getPort();
    return Airforce.builder().sessionToken("jwt-test").baseUrl(base).build();
  }

  private static void json(HttpExchange ex, int status, String body) throws IOException {
    byte[] bytes = body.getBytes(StandardCharsets.UTF_8);
    ex.getResponseHeaders().set("Content-Type", "application/json");
    ex.sendResponseHeaders(status, bytes.length);
    try (OutputStream os = ex.getResponseBody()) {
      os.write(bytes);
    }
  }

  @Test
  void chatCreate() throws IOException {
    AtomicReference<String> auth = new AtomicReference<>();
    AtomicReference<String> path = new AtomicReference<>();
    Airforce client = start(ex -> {
      auth.set(ex.getRequestHeaders().getFirst("authorization"));
      path.set(ex.getRequestURI().getPath());
      json(ex, 200, COMPLETION);
    });

    JsonNode res = client.chat().create(Map.of(
        "model", "claude-opus-4.8",
        "messages", List.of(Map.of("role", "user", "content", "hello"))));

    assertEquals("hi", res.get("choices").get(0).get("message").get("content").asText());
    assertEquals("Bearer sk-air-test", auth.get());
    assertEquals("/v1/chat/completions", path.get());
  }

  @Test
  void missingCredential() throws IOException {
    server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
    server.createContext("/", ex -> json(ex, 200, "{}"));
    server.start();
    Airforce client = Airforce.builder().baseUrl("http://127.0.0.1:" + server.getAddress().getPort()).build();

    assertThrows(AirforceException.MissingCredential.class, () -> client.chat().create(Map.of(
        "model", "m", "messages", List.of(Map.of("role", "user", "content", "x")))));
  }

  @Test
  void sessionEndpointRequiresSessionToken() throws IOException {
    // account().me() is a session endpoint; an API key must NOT be substituted.
    Airforce client = start(ex -> json(ex, 200, "{}"));
    assertThrows(AirforceException.MissingCredential.class, () -> client.account().me());
  }

  @Test
  void publicEndpointHasNoAuth() throws IOException {
    AtomicReference<String> auth = new AtomicReference<>("present");
    server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
    server.createContext("/", ex -> {
      auth.set(ex.getRequestHeaders().getFirst("authorization"));
      try {
        json(ex, 200, "{\"object\":\"list\",\"data\":[]}");
      } catch (IOException e) {
        throw new RuntimeException(e);
      }
    });
    server.start();
    Airforce client = Airforce.builder().baseUrl("http://127.0.0.1:" + server.getAddress().getPort()).build();

    client.models().list(false);
    assertNull(auth.get());
  }

  @Test
  void retryOn429() throws IOException {
    AtomicInteger calls = new AtomicInteger();
    Airforce client = start(ex -> {
      if (calls.incrementAndGet() == 1) {
        ex.getResponseHeaders().set("retry-after", "0");
        json(ex, 429, "{\"error\":\"slow\"}");
      } else {
        json(ex, 200, COMPLETION);
      }
    });

    JsonNode res = client.chat().create(Map.of(
        "model", "m", "messages", List.of(Map.of("role", "user", "content", "x"))));
    assertEquals("cmpl_1", res.get("id").asText());
    assertEquals(2, calls.get());
  }

  @Test
  void errorMapping() throws IOException {
    Airforce client = start(ex ->
        json(ex, 402, "{\"error\":{\"message\":\"no balance\",\"code\":\"insufficient_balance\"}}"));

    AirforceException err = assertThrows(AirforceException.class, () -> client.chat().create(Map.of(
        "model", "m", "messages", List.of(Map.of("role", "user", "content", "x")))));
    assertEquals(402, err.status());
    assertTrue(err.isInsufficientBalance());
    assertEquals("insufficient_balance", err.code());
  }

  @Test
  void embeddingsCreate() throws IOException {
    AtomicReference<String> auth = new AtomicReference<>();
    AtomicReference<String> path = new AtomicReference<>();
    AtomicReference<String> body = new AtomicReference<>();
    Airforce client = start(ex -> {
      auth.set(ex.getRequestHeaders().getFirst("authorization"));
      path.set(ex.getRequestURI().getPath());
      body.set(new String(ex.getRequestBody().readAllBytes(), StandardCharsets.UTF_8));
      json(ex, 200,
          "{\"object\":\"list\",\"data\":[{\"object\":\"embedding\",\"index\":0,\"embedding\":[0.1,0.2]}],"
              + "\"model\":\"embed-1\",\"usage\":{\"prompt_tokens\":2,\"total_tokens\":2}}");
    });

    JsonNode res = client.embeddings().create(Map.of("model", "embed-1", "input", "hello"));

    assertEquals("/v1/embeddings", path.get());
    assertEquals("Bearer sk-air-test", auth.get());
    assertTrue(body.get().contains("\"input\":\"hello\""));
    assertEquals(2, res.get("data").get(0).get("embedding").size());
    assertEquals(2, res.get("usage").get("prompt_tokens").asInt());
  }

  @Test
  void orgMembersList() throws IOException {
    AtomicReference<String> auth = new AtomicReference<>();
    AtomicReference<String> path = new AtomicReference<>();
    Airforce client = startSession(ex -> {
      auth.set(ex.getRequestHeaders().getFirst("authorization"));
      path.set(ex.getRequestURI().getPath());
      json(ex, 200, "{\"members\":[{\"user_id\":\"u1\",\"role\":\"owner\",\"status\":\"active\"}]}");
    });

    JsonNode members = client.org().members();

    assertEquals("/api/org/members", path.get());
    assertEquals("Bearer jwt-test", auth.get());
    assertTrue(members.isArray());
    assertEquals("owner", members.get(0).get("role").asText());
  }

  @Test
  void notificationsList() throws IOException {
    AtomicReference<String> path = new AtomicReference<>();
    AtomicReference<String> query = new AtomicReference<>();
    Airforce client = startSession(ex -> {
      path.set(ex.getRequestURI().getPath());
      query.set(ex.getRequestURI().getQuery());
      json(ex, 200,
          "{\"items\":[{\"id\":\"n1\",\"kind\":\"price_drop\",\"created_at\":\"2026-01-01T00:00:00Z\"}],\"unread\":1}");
    });

    JsonNode res = client.notifications().list(10, null);

    assertEquals("/api/me/notifications", path.get());
    assertEquals("limit=10", query.get());
    assertEquals(1, res.get("unread").asInt());
    assertEquals("n1", res.get("items").get(0).get("id").asText());
  }

  @Test
  void accountClose() throws IOException {
    AtomicReference<String> method = new AtomicReference<>();
    AtomicReference<String> path = new AtomicReference<>();
    AtomicReference<String> body = new AtomicReference<>();
    Airforce client = startSession(ex -> {
      method.set(ex.getRequestMethod());
      path.set(ex.getRequestURI().getPath());
      body.set(new String(ex.getRequestBody().readAllBytes(), StandardCharsets.UTF_8));
      json(ex, 200, "{\"closed\":true}");
    });

    JsonNode res = client.account().closeAccount(Map.of("password", "pw", "forfeit_balance_ack", true));

    assertEquals("DELETE", method.get());
    assertEquals("/api/me/account", path.get());
    assertTrue(body.get().contains("\"password\":\"pw\""));
    assertTrue(res.get("closed").asBoolean());
  }

  @Test
  void threeDGenerateAndWait() throws IOException {
    AtomicInteger polls = new AtomicInteger();
    Airforce client = start(ex -> {
      String p = ex.getRequestURI().getPath();
      if ("/v1/3d/generations".equals(p)) {
        json(ex, 200, "{\"task_id\":\"t3d_1\",\"status\":\"queued\",\"model\":\"m3d\",\"has_result\":false}");
      } else if (p.startsWith("/v1/3d/tasks/")) {
        json(ex, 200, polls.incrementAndGet() >= 2
            ? "{\"task_id\":\"t3d_1\",\"status\":\"completed\",\"has_result\":true,\"format\":\"glb\"}"
            : "{\"task_id\":\"t3d_1\",\"status\":\"processing\",\"has_result\":false}");
      } else {
        json(ex, 404, "{\"error\":\"not_found\"}");
      }
    });

    JsonNode task = client.threeD().generateAndWait(Map.of("model", "m3d", "prompt", "a cube"), 10, 5000);

    assertEquals("completed", task.get("status").asText());
    assertEquals("glb", task.get("format").asText());
    assertEquals(2, polls.get());
  }

  @Test
  void streaming() throws IOException {
    Airforce client = start(ex -> {
      ex.getResponseHeaders().set("Content-Type", "text/event-stream");
      ex.sendResponseHeaders(200, 0);
      try (OutputStream os = ex.getResponseBody()) {
        for (String chunk : new String[] {
            "data: {\"choices\":[{\"index\":0,\"delta\":{\"content\":\"he\"},\"finish_reason\":null}]}\n\n",
            "data: {\"choices\":[{\"index\":0,\"delta\":{\"content\":\"llo\"},\"finish_reason\":\"stop\"}]}\n\n",
            "data: [DONE]\n\n"}) {
          os.write(chunk.getBytes(StandardCharsets.UTF_8));
          os.flush();
        }
      }
    });

    StringBuilder text = new StringBuilder();
    try (Stream stream = client.chat().createStream(Map.of(
        "model", "m", "messages", List.of(Map.of("role", "user", "content", "x"))))) {
      for (JsonNode chunk : stream) {
        JsonNode content = chunk.get("choices").get(0).get("delta").get("content");
        if (content != null) {
          text.append(content.asText());
        }
      }
    }
    assertEquals("hello", text.toString());
  }
}
