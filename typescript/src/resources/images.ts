/**
 * Image generation — `POST /v1/images/generations`.
 */

import { APIResource, type RequestConfig } from "./resource";

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
}
