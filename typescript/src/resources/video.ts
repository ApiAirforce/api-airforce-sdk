/**
 * Video generation — `POST /v1/video/generations` and the async task API.
 */

import type { Stream } from "../core/streaming";
import { APIResource, type RequestConfig } from "./resource";
import { AirforceError } from "../core/errors";
import type { ImageInput } from "./images";

export type VideoMode = "text" | "image" | "reference";
export type VideoTaskStatus =
  | "queued"
  | "processing"
  | "completed"
  | "failed"
  | "expired";

export interface VideoGenerateParams {
  model: string;
  prompt: string;
  mode?: VideoMode;
  duration_seconds?: number;
  aspect_ratio?: string;
  quality?: string;
  input_images?: ImageInput[];
  [key: string]: unknown;
}

export interface VideoTask {
  task_id: string;
  status: VideoTaskStatus;
  model: string;
  created: number;
  progress?: number;
  result_url?: string;
  error?: string;
  cost_cents?: number;
  expires_at?: number;
  prompt?: string;
  mode?: VideoMode;
  duration_seconds?: number;
  aspect_ratio?: string;
  quality?: string;
  input_image_url?: string;
}

/**
 * One event from the video task SSE stream. The stream's `data:` payload is the
 * task state JSON (or an `{error}` object); the `[DONE]` sentinel ends iteration.
 * Read `status` to detect completion.
 */
export type VideoStreamEvent = VideoTask | { error: string };

export interface WaitOptions extends RequestConfig {
  /** Poll interval in ms. Default 2500. */
  pollIntervalMs?: number;
  /** Give up after this many ms. Default 600000 (10 min). */
  timeoutMs?: number;
}

const TERMINAL: ReadonlySet<VideoTaskStatus> = new Set([
  "completed",
  "failed",
  "expired",
]);

export class Video extends APIResource {
  /** Create an async video generation task. */
  generate(
    params: VideoGenerateParams,
    options: RequestConfig = {},
  ): Promise<VideoTask> {
    return this.transport.request({
      method: "POST",
      path: "/v1/video/generations",
      body: params,
      ...options,
    });
  }

  /** Get the current state of a task. */
  getTask(id: string, options: RequestConfig = {}): Promise<VideoTask> {
    return this.transport.request({
      method: "GET",
      path: `/v1/video/tasks/${encodeURIComponent(id)}`,
      ...options,
    });
  }

  /** List the caller's recent tasks (≤100, newest first). */
  async listTasks(options: RequestConfig = {}): Promise<VideoTask[]> {
    const res = await this.transport.request<{ data: VideoTask[] }>({
      method: "GET",
      path: "/v1/video/tasks",
      ...options,
    });
    return res.data;
  }

  /** Remove a task from the caller's history. */
  deleteTask(
    id: string,
    options: RequestConfig = {},
  ): Promise<{ deleted: boolean }> {
    return this.transport.request({
      method: "DELETE",
      path: `/v1/video/tasks/${encodeURIComponent(id)}`,
      ...options,
    });
  }

  /** Stream task state changes via SSE. */
  streamTask(
    id: string,
    options: RequestConfig = {},
  ): Promise<Stream<VideoStreamEvent>> {
    return this.transport.stream({
      method: "GET",
      path: `/v1/video/tasks/${encodeURIComponent(id)}/stream`,
      ...options,
    });
  }

  /**
   * Convenience: create a task and poll until it reaches a terminal state.
   * Resolves with the completed task or throws on `failed`/`expired`/timeout.
   */
  async generateAndWait(
    params: VideoGenerateParams,
    options: WaitOptions = {},
  ): Promise<VideoTask> {
    const task = await this.generate(params, options);
    return this.waitForCompletion(task.task_id, options);
  }

  /** Poll a task until it finishes. */
  async waitForCompletion(
    id: string,
    options: WaitOptions = {},
  ): Promise<VideoTask> {
    const interval = options.pollIntervalMs ?? 2500;
    const deadline = Date.now() + (options.timeoutMs ?? 600_000);
    for (;;) {
      const task = await this.getTask(id, options);
      if (TERMINAL.has(task.status)) {
        if (task.status !== "completed") {
          throw new AirforceError(
            `Video task ${id} ended with status "${task.status}"${
              task.error ? `: ${task.error}` : ""
            }`,
            { code: task.status, body: task },
          );
        }
        return task;
      }
      if (Date.now() > deadline) {
        throw new AirforceError(`Timed out waiting for video task ${id}`, {
          code: "wait_timeout",
          body: task,
        });
      }
      await new Promise((r) => setTimeout(r, interval));
    }
  }
}
