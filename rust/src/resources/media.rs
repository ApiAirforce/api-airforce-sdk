use super::{build_multipart, enc};
use crate::client::Client;
use crate::error::{Error, Result};
use reqwest::Method;
use serde::Serialize;
use serde_json::Value;
use std::time::Duration;

/// Image generation — `POST /v1/images/generations`.
pub struct Images<'a> {
    pub(crate) client: &'a Client,
}

impl Images<'_> {
    pub async fn generate(&self, request: impl Serialize) -> Result<Value> {
        let body = serde_json::to_value(request)?;
        self.client
            .request_json(
                Method::POST,
                "/v1/images/generations",
                "api_key",
                Some(body),
            )
            .await
    }
}

/// Audio — TTS, music, SFX, transcription, dubbing, voices (`/v1/audio/*`).
pub struct Audio<'a> {
    pub(crate) client: &'a Client,
}

impl Audio<'_> {
    pub async fn speech(&self, request: impl Serialize) -> Result<Vec<u8>> {
        let body = serde_json::to_value(request)?;
        self.client
            .request_bytes(Method::POST, "/v1/audio/speech", "api_key", Some(body))
            .await
    }

    pub async fn music(&self, request: impl Serialize) -> Result<Vec<u8>> {
        let body = serde_json::to_value(request)?;
        self.client
            .request_bytes(Method::POST, "/v1/audio/music", "api_key", Some(body))
            .await
    }

    pub async fn sound_effects(&self, request: impl Serialize) -> Result<Vec<u8>> {
        let body = serde_json::to_value(request)?;
        self.client
            .request_bytes(
                Method::POST,
                "/v1/audio/sound-effects",
                "api_key",
                Some(body),
            )
            .await
    }

    pub async fn transcriptions(
        &self,
        model: &str,
        file: &[u8],
        filename: &str,
        extra: &[(&str, &str)],
    ) -> Result<Value> {
        let fields = fields(model, extra);
        let (body, ct) = build_multipart(&fields, &[("file", filename, file)]);
        self.client
            .multipart_json("/v1/audio/transcriptions", "api_key", body, &ct)
            .await
    }

    pub async fn audio_isolation(
        &self,
        model: &str,
        file: &[u8],
        filename: &str,
        output: Option<&str>,
    ) -> Result<Vec<u8>> {
        let mut fields = vec![("model", model.to_string())];
        if let Some(o) = output {
            fields.push(("output", o.to_string()));
        }
        let (body, ct) = build_multipart(&fields, &[("file", filename, file)]);
        self.client
            .multipart_bytes("/v1/audio/audio-isolation", "api_key", body, &ct)
            .await
    }

    pub async fn voice_changer(
        &self,
        model: &str,
        file: &[u8],
        filename: &str,
        voice: &str,
    ) -> Result<Vec<u8>> {
        let fields = vec![("model", model.to_string()), ("voice", voice.to_string())];
        let (body, ct) = build_multipart(&fields, &[("file", filename, file)]);
        self.client
            .multipart_bytes("/v1/audio/voice-changer", "api_key", body, &ct)
            .await
    }

    pub async fn dubbing(
        &self,
        model: &str,
        file: &[u8],
        filename: &str,
        target_lang: &str,
        extra: &[(&str, &str)],
    ) -> Result<Value> {
        let mut fields = fields(model, extra);
        fields.push(("target_lang", target_lang.to_string()));
        let (body, ct) = build_multipart(&fields, &[("file", filename, file)]);
        self.client
            .multipart_json("/v1/audio/dubbing", "api_key", body, &ct)
            .await
    }

    pub async fn dubbing_status(&self, id: &str) -> Result<Value> {
        self.client
            .get_json(&format!("/v1/audio/dubbing/{}", enc(id)), "api_key", None)
            .await
    }

    pub async fn dubbing_audio(&self, id: &str, lang: &str) -> Result<Vec<u8>> {
        let path = format!("/v1/audio/dubbing/{}/audio/{}", enc(id), enc(lang));
        self.client
            .request_bytes(Method::GET, &path, "api_key", None)
            .await
    }

    pub async fn voices(&self) -> Result<Value> {
        let res = self
            .client
            .get_json("/v1/audio/voices", "api_key", None)
            .await?;
        Ok(res.get("voices").cloned().unwrap_or(res))
    }
}

fn fields<'a>(model: &'a str, extra: &[(&'a str, &str)]) -> Vec<(&'a str, String)> {
    let mut fields = vec![("model", model.to_string())];
    for &(k, v) in extra {
        fields.push((k, v.to_string()));
    }
    fields
}

/// Async video generation — `/v1/video/*`.
pub struct Video<'a> {
    pub(crate) client: &'a Client,
}

impl Video<'_> {
    pub async fn generate(&self, request: impl Serialize) -> Result<Value> {
        let body = serde_json::to_value(request)?;
        self.client
            .request_json(Method::POST, "/v1/video/generations", "api_key", Some(body))
            .await
    }

    pub async fn get_task(&self, id: &str) -> Result<Value> {
        self.client
            .get_json(&format!("/v1/video/tasks/{}", enc(id)), "api_key", None)
            .await
    }

    pub async fn list_tasks(&self) -> Result<Value> {
        let res = self
            .client
            .get_json("/v1/video/tasks", "api_key", None)
            .await?;
        Ok(res.get("data").cloned().unwrap_or(res))
    }

    pub async fn delete_task(&self, id: &str) -> Result<Value> {
        self.client
            .request_json(
                Method::DELETE,
                &format!("/v1/video/tasks/{}", enc(id)),
                "api_key",
                None,
            )
            .await
    }

    /// Poll a task until it reaches a terminal state.
    pub async fn wait_for_completion(
        &self,
        id: &str,
        poll: Duration,
        timeout: Duration,
    ) -> Result<Value> {
        let deadline = tokio::time::Instant::now() + timeout;
        loop {
            let task = self.get_task(id).await?;
            match task.get("status").and_then(Value::as_str).unwrap_or("") {
                "completed" => return Ok(task),
                s @ ("failed" | "expired") => {
                    return Err(Error::custom(
                        s,
                        format!("video task {id} ended with status {s}"),
                    ))
                }
                _ => {}
            }
            if tokio::time::Instant::now() > deadline {
                return Err(Error::custom(
                    "wait_timeout",
                    format!("timed out waiting for video task {id}"),
                ));
            }
            tokio::time::sleep(poll).await;
        }
    }

    pub async fn generate_and_wait(
        &self,
        request: impl Serialize,
        poll: Duration,
        timeout: Duration,
    ) -> Result<Value> {
        let task = self.generate(request).await?;
        let id = task
            .get("task_id")
            .and_then(Value::as_str)
            .ok_or_else(|| {
                Error::custom(
                    "invalid_response",
                    "video task response had no task_id".into(),
                )
            })?
            .to_string();
        self.wait_for_completion(&id, poll, timeout).await
    }
}

/// Voice cloning — `/v1/voices/*`.
pub struct Voices<'a> {
    pub(crate) client: &'a Client,
}

impl Voices<'_> {
    pub async fn consent_text(&self) -> Result<Value> {
        self.client
            .get_json("/v1/voices/consent-text", "none", None)
            .await
    }

    /// Create a cloned voice from one or more samples (filename + bytes).
    pub async fn clone(
        &self,
        name: &str,
        consent_hash: &str,
        samples: &[(&str, &[u8])],
        extra: &[(&str, &str)],
    ) -> Result<Value> {
        let mut fields = vec![
            ("name", name.to_string()),
            ("consent_hash", consent_hash.to_string()),
        ];
        for &(k, v) in extra {
            fields.push((k, v.to_string()));
        }
        let files: Vec<(&str, &str, &[u8])> = samples
            .iter()
            .map(|(fname, data)| ("files", *fname, *data))
            .collect();
        let (body, ct) = build_multipart(&fields, &files);
        self.client
            .multipart_json("/v1/voices/clone", "api_key", body, &ct)
            .await
    }

    pub async fn library(&self) -> Result<Value> {
        let res = self
            .client
            .get_json("/v1/voices/library", "api_key", None)
            .await?;
        Ok(res.get("voices").cloned().unwrap_or(res))
    }

    pub async fn update(&self, voice_id: &str, body: impl Serialize) -> Result<Value> {
        let body = serde_json::to_value(body)?;
        self.client
            .request_json(
                Method::PATCH,
                &format!("/v1/voices/clone/{}", enc(voice_id)),
                "api_key",
                Some(body),
            )
            .await
    }

    pub async fn delete(&self, voice_id: &str) -> Result<Value> {
        self.client
            .request_json(
                Method::DELETE,
                &format!("/v1/voices/clone/{}", enc(voice_id)),
                "api_key",
                None,
            )
            .await
    }
}
