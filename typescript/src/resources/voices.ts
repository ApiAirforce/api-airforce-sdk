/**
 * Voice cloning — `/v1/voices/*`.
 */

import { APIResource, type RequestConfig } from "./resource";
import type { FileLike } from "./audio";

function toBlob(file: FileLike): Blob {
  return file instanceof Blob ? file : new Blob([file as BlobPart]);
}

export interface ConsentText {
  text: string;
  hash: string;
}

export interface CloneVoiceParams {
  name: string;
  /** Audio samples (one or more). */
  files: Array<{ value: FileLike; name?: string }>;
  /** SHA-256 hash from {@link Voices.consentText}. */
  consent_hash: string;
  description?: string;
  /** JSON-encoded ElevenLabs labels. */
  labels?: string;
  remove_background_noise?: boolean;
}

export interface ClonedVoice {
  voice_id?: string;
  provider_voice_id?: string;
  name: string;
  description?: string;
  status: string;
  created_at?: string;
  provider?: string;
  last_error?: string;
}

export class Voices extends APIResource {
  /** Fetch the current consent paragraph + its hash (public, no auth). */
  consentText(options: RequestConfig = {}): Promise<ConsentText> {
    return this.transport.request({
      method: "GET",
      path: "/v1/voices/consent-text",
      auth: "none",
      ...options,
    });
  }

  /** Create a cloned voice from one or more audio samples. */
  clone(
    params: CloneVoiceParams,
    options: RequestConfig = {},
  ): Promise<ClonedVoice> {
    const form = new FormData();
    form.append("name", params.name);
    form.append("consent_hash", params.consent_hash);
    if (params.description) form.append("description", params.description);
    if (params.labels) form.append("labels", params.labels);
    if (params.remove_background_noise !== undefined) {
      form.append(
        "remove_background_noise",
        String(params.remove_background_noise),
      );
    }
    for (const f of params.files) {
      form.append("files", toBlob(f.value), f.name ?? "sample");
    }
    return this.transport.request({
      method: "POST",
      path: "/v1/voices/clone",
      form,
      ...options,
    });
  }

  /** List the caller's cloned voices. */
  async library(options: RequestConfig = {}): Promise<ClonedVoice[]> {
    const res = await this.transport.request<{ voices: ClonedVoice[] }>({
      method: "GET",
      path: "/v1/voices/library",
      ...options,
    });
    return res.voices;
  }

  /** Rename or update a cloned voice (local record). */
  update(
    voiceId: string,
    body: { name?: string; description?: string },
    options: RequestConfig = {},
  ): Promise<{ updated: boolean; voice_id: string }> {
    return this.transport.request({
      method: "PATCH",
      path: `/v1/voices/clone/${encodeURIComponent(voiceId)}`,
      body,
      ...options,
    });
  }

  /** Delete a cloned voice from provider and local library. */
  delete(
    voiceId: string,
    options: RequestConfig = {},
  ): Promise<{ deleted: boolean; voice_id: string }> {
    return this.transport.request({
      method: "DELETE",
      path: `/v1/voices/clone/${encodeURIComponent(voiceId)}`,
      ...options,
    });
  }
}
