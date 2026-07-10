package com.airforce;

import com.fasterxml.jackson.databind.JsonNode;
import java.util.Map;

/**
 * Async 3D model generation — {@code /v1/3d/*}. Tasks and their stored artifacts expire
 * after 24 hours; credits are deducted only when a worker picks up the task, and failures
 * are refunded.
 */
public final class ThreeDResource extends Resource {

  ThreeDResource(Transport transport) {
    super(transport);
  }

  /**
   * Create an async 3D generation task. Requires {@code model}; image-to-3D models also
   * require at least one {@code image_urls} entry (http(s) URL or data: URI, max 4).
   * Optional keys: resolution ('low'|'medium'|'high'), prompt. Extra fields are forwarded.
   */
  public JsonNode generate(Map<String, Object> params) {
    return transport.post("/v1/3d/generations", "api_key", params);
  }

  /** Get the current state of a task (foreign or unknown tasks are a 404). */
  public JsonNode getTask(String id) {
    return transport.get("/v1/3d/tasks/" + enc(id), "api_key", null);
  }

  /** List the caller's recent tasks, newest first (returns the {@code data} array). */
  public JsonNode listTasks() {
    JsonNode res = transport.get("/v1/3d/tasks", "api_key", null);
    return res != null && res.has("data") ? res.get("data") : res;
  }

  /**
   * Download the finished model artifact as raw bytes (glb or ply, per the task's
   * {@code format}); 404 until the task reports {@code has_result}.
   */
  public byte[] downloadContent(String id) {
    return transport.getBytes("/v1/3d/tasks/" + enc(id) + "/content", "api_key");
  }

  /** Remove a task and its artifact from history (idempotent). */
  public JsonNode deleteTask(String id) {
    return transport.delete("/v1/3d/tasks/" + enc(id), "api_key");
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
        throw new AirforceException("airforce: 3d task " + id + " ended with status " + status);
      }
      if (System.currentTimeMillis() > deadline) {
        throw new AirforceException("airforce: timed out waiting for 3d task " + id);
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
