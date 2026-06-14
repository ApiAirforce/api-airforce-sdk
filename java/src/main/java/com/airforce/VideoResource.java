package com.airforce;

import com.fasterxml.jackson.databind.JsonNode;
import java.util.Map;

/** Async video generation — {@code /v1/video/*}. */
public final class VideoResource extends Resource {

  VideoResource(Transport transport) {
    super(transport);
  }

  /** Create an async video task. Requires {@code model} and {@code prompt}. */
  public JsonNode generate(Map<String, Object> params) {
    return transport.post("/v1/video/generations", "api_key", params);
  }

  /** Get the current state of a task. */
  public JsonNode getTask(String id) {
    return transport.get("/v1/video/tasks/" + enc(id), "api_key", null);
  }

  /** List the caller's recent tasks (returns the {@code data} array). */
  public JsonNode listTasks() {
    JsonNode res = transport.get("/v1/video/tasks", "api_key", null);
    return res != null && res.has("data") ? res.get("data") : res;
  }

  /** Remove a task from history. */
  public JsonNode deleteTask(String id) {
    return transport.delete("/v1/video/tasks/" + enc(id), "api_key");
  }

  /** Poll a task until it reaches a terminal state. */
  public JsonNode waitForCompletion(String id, long pollMillis, long timeoutMillis) {
    long interval = pollMillis > 0 ? pollMillis : 2500;
    long deadline = System.currentTimeMillis() + (timeoutMillis > 0 ? timeoutMillis : 600_000);
    while (true) {
      JsonNode task = getTask(id);
      String status = task != null && task.has("status") ? task.get("status").asText() : "";
      if ("completed".equals(status)) {
        return task;
      }
      if ("failed".equals(status) || "expired".equals(status)) {
        throw new AirforceException("airforce: video task " + id + " ended with status " + status);
      }
      if (System.currentTimeMillis() > deadline) {
        throw new AirforceException("airforce: timed out waiting for video task " + id);
      }
      try {
        Thread.sleep(interval);
      } catch (InterruptedException e) {
        Thread.currentThread().interrupt();
        throw new AirforceException.ApiConnection("airforce: wait interrupted", e);
      }
    }
  }

  /** Create a task and wait for completion. */
  public JsonNode generateAndWait(Map<String, Object> params, long pollMillis, long timeoutMillis) {
    JsonNode task = generate(params);
    return waitForCompletion(task.get("task_id").asText(), pollMillis, timeoutMillis);
  }
}
