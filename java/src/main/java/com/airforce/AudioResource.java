package com.airforce;

import com.fasterxml.jackson.databind.JsonNode;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;

/** Audio — TTS, music, SFX, transcription, dubbing, voices ({@code /v1/audio/*}). */
public final class AudioResource extends Resource {

  AudioResource(Transport transport) {
    super(transport);
  }

  /** Text-to-speech. Returns raw audio bytes. Requires model, input, voice. */
  public byte[] speech(Map<String, Object> params) {
    return transport.postBytes("/v1/audio/speech", "api_key", params);
  }

  /** Generate music. Returns raw audio bytes. Requires model, prompt. */
  public byte[] music(Map<String, Object> params) {
    return transport.postBytes("/v1/audio/music", "api_key", params);
  }

  /** Generate a sound effect. Returns raw audio bytes. Requires model, prompt. */
  public byte[] soundEffects(Map<String, Object> params) {
    return transport.postBytes("/v1/audio/sound-effects", "api_key", params);
  }

  /** Transcribe an audio/video file. {@code extra} may carry language, prompt, temperature. */
  public JsonNode transcriptions(String model, byte[] file, String filename, Map<String, String> extra) {
    return multipartJson("/v1/audio/transcriptions", fields(model, extra),
        new Multipart.FilePart("file", filename, file));
  }

  /** Isolate vocals/instrumental. Returns raw audio bytes. */
  public byte[] audioIsolation(String model, byte[] file, String filename, String output) {
    Map<String, String> fields = new HashMap<>();
    fields.put("model", model);
    if (output != null) {
      fields.put("output", output);
    }
    return multipartBytes("/v1/audio/audio-isolation", fields, new Multipart.FilePart("file", filename, file));
  }

  /** Apply a target voice to an audio file. Returns raw audio bytes. */
  public byte[] voiceChanger(String model, byte[] file, String filename, String voice) {
    Map<String, String> fields = new HashMap<>();
    fields.put("model", model);
    fields.put("voice", voice);
    return multipartBytes("/v1/audio/voice-changer", fields, new Multipart.FilePart("file", filename, file));
  }

  /** Start an async dubbing job. {@code extra} may carry source_lang, etc. */
  public JsonNode dubbing(String model, byte[] file, String filename, String targetLang, Map<String, String> extra) {
    Map<String, String> fields = fields(model, extra);
    fields.put("target_lang", targetLang);
    return multipartJson("/v1/audio/dubbing", fields, new Multipart.FilePart("file", filename, file));
  }

  /** Poll a dubbing job. */
  public JsonNode dubbingStatus(String id) {
    return transport.get("/v1/audio/dubbing/" + enc(id), "api_key", null);
  }

  /** Fetch the dubbed audio for a completed job. */
  public byte[] dubbingAudio(String id, String lang) {
    return transport.getBytes("/v1/audio/dubbing/" + enc(id) + "/audio/" + enc(lang), "api_key");
  }

  /** List available TTS voices (returns the {@code voices} array). */
  public JsonNode voices() {
    JsonNode res = transport.get("/v1/audio/voices", "api_key", null);
    return res != null && res.has("voices") ? res.get("voices") : res;
  }

  private static Map<String, String> fields(String model, Map<String, String> extra) {
    Map<String, String> fields = new HashMap<>();
    fields.put("model", model);
    if (extra != null) {
      fields.putAll(extra);
    }
    return fields;
  }

  private JsonNode multipartJson(String path, Map<String, String> fields, Multipart.FilePart file) {
    Multipart m = Multipart.build(fields, Collections.singletonList(file));
    Transport.RequestSpec spec = new Transport.RequestSpec();
    spec.auth = "api_key";
    spec.rawBody = m.body;
    spec.contentType = m.contentType;
    return transport.requestJson("POST", path, spec);
  }

  private byte[] multipartBytes(String path, Map<String, String> fields, Multipart.FilePart file) {
    Multipart m = Multipart.build(fields, Collections.singletonList(file));
    Transport.RequestSpec spec = new Transport.RequestSpec();
    spec.auth = "api_key";
    spec.rawBody = m.body;
    spec.contentType = m.contentType;
    return transport.requestBytes("POST", path, spec);
  }
}
