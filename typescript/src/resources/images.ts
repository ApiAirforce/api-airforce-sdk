/**
 * Image generation — `POST /v1/images/generations` — and edits —
 * `POST /v1/images/edits`.
 */

import { APIResource, type RequestConfig } from "./resource";
import type { FileLike } from "./audio";

function toBlob(file: FileLike): Blob {
  return file instanceof Blob ? file : new Blob([file as BlobPart]);
}

export interface ImageInput {
  url?: string;
  b64_json?: string;
}

export interface ImageGenerateParams {
  model: string;
  prompt: string;
  n?: number;
  size?: string;
  quality?: string;
  response_format?: "url" | "b64_json";
  aspect_ratio?: string;
  /** Reference images for image-to-image / edit modes. */
  input_images?: ImageInput[];
  /** airforce: fallback model names. */
  models?: string[];
  /** Pass-through for provider-specific fields (seed, etc.). */
  [key: string]: unknown;
}

export interface ImagesResponse {
  created?: number;
  data: ImageInput[];
}

export interface ImageEditParams {
  model: string;
  prompt: string;
  /** Input images: at least one, at most 16, 25 MB each. */
  images: Array<{ value: FileLike; name?: string }>;
  /** Optional mask, forwarded as is (no listed model declares mask support). */
  mask?: { value: FileLike; name?: string };
  n?: number;
  size?: string;
  aspect_ratio?: string;
  quality?: string;
  response_format?: "url" | "b64_json";
  /** Pass-through for other form fields. */
  [key: string]: unknown;
}

export class Images extends APIResource {
  /** Generate one or more images from a text prompt. */
  generate(
    params: ImageGenerateParams,
    options: RequestConfig = {},
  ): Promise<ImagesResponse> {
    return this.transport.request({
      method: "POST",
      path: "/v1/images/generations",
      body: params,
      ...options,
    });
  }

  /**
   * Edit or vary input image(s) (multipart). Same models, prices and response
   * shape as {@link Images.generate}.
   */
  edit(params: ImageEditParams, options: RequestConfig = {}): Promise<ImagesResponse> {
    const { images, mask, ...fields } = params;
    const form = new FormData();
    for (const [k, v] of Object.entries(fields)) {
      if (v === undefined || v === null) continue;
      form.append(k, typeof v === "string" ? v : JSON.stringify(v));
    }
    for (const img of images) {
      form.append("image", toBlob(img.value), img.name ?? "image.png");
    }
    if (mask) form.append("mask", toBlob(mask.value), mask.name ?? "mask.png");
    return this.transport.request({
      method: "POST",
      path: "/v1/images/edits",
      form,
      ...options,
    });
  }
}
