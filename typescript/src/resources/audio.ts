/**
 * Audio — `/v1/audio/*`: text-to-speech, music, sound effects, transcription,
 * isolation, voice-changer, dubbing, and voice listing.
 *
 * JSON endpoints (speech/music/sfx) return raw audio bytes as an ArrayBuffer.
 * Multipart endpoints accept a file as `Blob | ArrayBuffer | Uint8Array`.
 */

import { APIResource, type RequestConfig } from "./resource";

export type FileLike = Blob | ArrayBuffer | Uint8Array;

function toBlob(file: FileLike): Blob {
  if (file instanceof Blob) return file;
  return new Blob([file as BlobPart]);
}

function buildForm(
  fields: Record<string, unknown>,
  file?: { value: FileLike; name?: string },
): FormData {
  const form = new FormData();
  for (const [k, v] of Object.entries(fields)) {
    if (v === undefined || v === null) continue;
    form.append(k, typeof v === "string" ? v : JSON.stringify(v));
  }
  if (file) form.append("file", toBlob(file.value), file.name ?? "file");
  return form;
}

export interface VoiceSettings {
  stability?: number;
  similarity_boost?: number;
  style?: number;
  use_speaker_boost?: boolean;
  speed?: number;
}

export interface SpeechParams {
  model: string;
  input: string;
  voice: string;
  response_format?: string;
  speed?: number;
  voice_settings?: VoiceSettings;
  language_code?: string;
  seed?: number;
  [key: string]: unknown;
}

export interface MusicParams {
  model: string;
  prompt: string;
  music_length_ms?: number;
  response_format?: string;
  composition_plan?: Record<string, unknown>;
}

export interface SoundEffectParams {
  model: string;
  prompt: string;
  duration_seconds?: number;
  prompt_influence?: number;
  response_format?: string;
}

export interface TranscriptionParams {
  model: string;
  file: FileLike;
  filename?: string;
  language?: string;
  prompt?: string;
  temperature?: number;
}

export interface Transcription {
  text: string;
  language: string;
  duration: number;
}

export interface VoiceChangerParams {
  model: string;
  file: FileLike;
  filename?: string;
  voice: string;
  voice_settings?: VoiceSettings;
}

export interface DubbingParams {
  model: string;
  file: FileLike;
  filename?: string;
  target_lang: string;
  source_lang?: string;
  num_speakers?: number;
  drop_background_audio?: boolean;
  watermark?: boolean;
  name?: string;
  [key: string]: unknown;
}

export interface DubbingJob {
  dubbing_id: string;
  status: string;
  language_pairs?: Array<{ source: string; target: string }>;
  source_duration?: number;
  preview_url?: string;
  error?: string;
}

export interface Voice {
  voice_id: string;
  name: string;
  preview_url?: string;
  category?: string;
  language?: string;
  accent?: string;
  age?: string;
  gender?: string;
  use_case?: string;
  description?: string;
}

export class Audio extends APIResource {
  /** Text-to-speech. Returns raw audio bytes. */
  speech(params: SpeechParams, options: RequestConfig = {}): Promise<ArrayBuffer> {
    return this.transport.requestBinary({
      method: "POST",
      path: "/v1/audio/speech",
      body: params,
      ...options,
    });
  }

  /** Generate music. Returns raw audio bytes. */
  music(params: MusicParams, options: RequestConfig = {}): Promise<ArrayBuffer> {
    return this.transport.requestBinary({
      method: "POST",
      path: "/v1/audio/music",
      body: params,
      ...options,
    });
  }

  /** Generate a sound effect. Returns raw audio bytes. */
  soundEffects(
    params: SoundEffectParams,
    options: RequestConfig = {},
  ): Promise<ArrayBuffer> {
    return this.transport.requestBinary({
      method: "POST",
      path: "/v1/audio/sound-effects",
      body: params,
      ...options,
    });
  }

  /** Transcribe an audio/video file to text. */
  transcriptions(
    params: TranscriptionParams,
    options: RequestConfig = {},
  ): Promise<Transcription> {
    const { file, filename, ...fields } = params;
    return this.transport.request({
      method: "POST",
      path: "/v1/audio/transcriptions",
      form: buildForm(fields, { value: file, name: filename }),
      ...options,
    });
  }

  /** Isolate vocals/instrumental from an audio file. Returns audio bytes. */
  audioIsolation(
    params: { model: string; file: FileLike; filename?: string; output?: string },
    options: RequestConfig = {},
  ): Promise<ArrayBuffer> {
    const { file, filename, ...fields } = params;
    return this.transport.requestBinary({
      method: "POST",
      path: "/v1/audio/audio-isolation",
      form: buildForm(fields, { value: file, name: filename }),
      ...options,
    });
  }

  /** Apply a target voice to an audio file. Returns audio bytes. */
  voiceChanger(
    params: VoiceChangerParams,
    options: RequestConfig = {},
  ): Promise<ArrayBuffer> {
    const { file, filename, ...fields } = params;
    return this.transport.requestBinary({
      method: "POST",
      path: "/v1/audio/voice-changer",
      form: buildForm(fields, { value: file, name: filename }),
      ...options,
    });
  }

  /** Start an async dubbing job. Returns the job id to poll. */
  dubbing(params: DubbingParams, options: RequestConfig = {}): Promise<DubbingJob> {
    const { file, filename, ...fields } = params;
    return this.transport.request({
      method: "POST",
      path: "/v1/audio/dubbing",
      form: buildForm(fields, { value: file, name: filename }),
      ...options,
    });
  }

  /** Poll a dubbing job's status. */
  dubbingStatus(id: string, options: RequestConfig = {}): Promise<DubbingJob> {
    return this.transport.request({
      method: "GET",
      path: `/v1/audio/dubbing/${encodeURIComponent(id)}`,
      ...options,
    });
  }

  /** Fetch the dubbed audio for a completed job (raw bytes). */
  dubbingAudio(
    id: string,
    lang: string,
    options: RequestConfig = {},
  ): Promise<ArrayBuffer> {
    return this.transport.requestBinary({
      method: "GET",
      path: `/v1/audio/dubbing/${encodeURIComponent(id)}/audio/${encodeURIComponent(lang)}`,
      ...options,
    });
  }

  /** List available voices (provider + user-cloned). */
  async voices(options: RequestConfig = {}): Promise<Voice[]> {
    const res = await this.transport.request<{ voices: Voice[] }>({
      method: "GET",
      path: "/v1/audio/voices",
      ...options,
    });
    return res.voices;
  }
}
