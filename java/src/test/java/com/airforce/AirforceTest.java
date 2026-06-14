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
