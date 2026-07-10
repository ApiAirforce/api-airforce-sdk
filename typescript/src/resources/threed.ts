/**
 * 3D generation — `POST /v1/3d/generations` and the async task API.
 *
 * Mirrors the video task model: create a task, poll until it completes, then
 * download the model artifact. Tasks are owner-checked (foreign/missing tasks
 * are an indistinguishable 404) and expire — with their stored artifact —
 * after 24 h. Credits are deducted only when the worker claims the task;
 * failures are refunded.
 */

import { APIResource, type RequestConfig } from "./resource";
import { AirforceError } from "../core/errors";
import type { WaitOptions } from "./video";

export type { WaitOptions } from "./video";

export type ThreeDResolution = "low" | "medium" | "high";
export type ThreeDTaskStatus =
  | "queued"
  | "processing"
  | "completed"
  | "failed"
  | "expired";
export type ThreeDFormat = "glb" | "ply";

export interface ThreeDGenerateParams {
  model: string;
  /**
   * Source images (http(s) URL or `data:` URI, max 4). Image-to-3D models
   * require at least one entry. URLs are validated at submit time.
   */
  image_urls?: string[];
  resolution?: ThreeDResolution;
  prompt?: string;
  /** Pass-through for provider-specific fields. */
  [key: string]: unknown;
}

export interface ThreeDTask {
  task_id: string;
  status: ThreeDTaskStatus;
  model: string;
  created: number;
  error?: string;
  cost_cents?: number;
  expires_at: number;
  /** True once the artifact can be downloaded via {@link ThreeD.downloadContent}. */
  has_result: boolean;
  /** Artifact format, set on completion. */
  format?: ThreeDFormat;
  resolution?: ThreeDResolution;
  input_image_url?: string;
}

const TERMINAL: ReadonlySet<ThreeDTaskStatus> = new Set([
  "completed",
  "failed",
  "expired",
]);

export class ThreeD extends APIResource {
  /** Create an async 3D generation task. */
  generate(
    params: ThreeDGenerateParams,
    options: RequestConfig = {},
  ): Promise<ThreeDTask> {
    return this.transport.request({
      method: "POST",
      path: "/v1/3d/generations",
      body: params,
      ...options,
    });
  }

  /** Get the current state of a task. */
  getTask(id: string, options: RequestConfig = {}): Promise<ThreeDTask> {
    return this.transport.request({
      method: "GET",
      path: `/v1/3d/tasks/${encodeURIComponent(id)}`,
      ...options,
    });
  }

  /** List the caller's recent tasks (≤100, newest first). */
  async listTasks(options: RequestConfig = {}): Promise<ThreeDTask[]> {
    const res = await this.transport.request<{ data: ThreeDTask[] }>({
      method: "GET",
      path: "/v1/3d/tasks",
      ...options,
    });
    return res.data;
  }

  /** Remove a task and its artifact from the caller's history (idempotent). */
  deleteTask(
    id: string,
    options: RequestConfig = {},
  ): Promise<{ deleted: boolean }> {
    return this.transport.request({
      method: "DELETE",
      path: `/v1/3d/tasks/${encodeURIComponent(id)}`,
      ...options,
    });
  }

  /**
   * Download the finished model artifact as raw bytes (`model/gltf-binary`
   * for glb, `application/octet-stream` for ply). 404 until `has_result`.
   */
  downloadContent(
    id: string,
    options: RequestConfig = {},
  ): Promise<ArrayBuffer> {
    return this.transport.requestBinary({
      method: "GET",
      path: `/v1/3d/tasks/${encodeURIComponent(id)}/content`,
      ...options,
    });
  }

  /**
   * Convenience: create a task and poll until it reaches a terminal state.
   * Resolves with the completed task or throws on `failed`/`expired`/timeout.
   */
  async generateAndWait(
    params: ThreeDGenerateParams,
    options: WaitOptions = {},
  ): Promise<ThreeDTask> {
    const task = await this.generate(params, options);
    return this.waitForCompletion(task.task_id, options);
  }

  /** Poll a task until it finishes. */
  async waitForCompletion(
    id: string,
    options: WaitOptions = {},
  ): Promise<ThreeDTask> {
    const interval = options.pollIntervalMs ?? 2500;
    const deadline = Date.now() + (options.timeoutMs ?? 600_000);
    for (;;) {
      const task = await this.getTask(id, options);
      if (TERMINAL.has(task.status)) {
        if (task.status !== "completed") {
          throw new AirforceError(
            `3D task ${id} ended with status "${task.status}"${
              task.error ? `: ${task.error}` : ""
            }`,
            { code: task.status, body: task },
          );
        }
        return task;
      }
      if (Date.now() > deadline) {
        throw new AirforceError(`Timed out waiting for 3D task ${id}`, {
          code: "wait_timeout",
          body: task,
        });
      }
      await new Promise((r) => setTimeout(r, interval));
    }
  }
}
