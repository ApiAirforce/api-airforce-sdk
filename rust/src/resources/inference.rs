use super::{enc, with_stream};
use crate::client::Client;
use crate::error::Result;
use crate::sse::parse_sse;
use futures::Stream;
use reqwest::Method;
use serde::Serialize;
use serde_json::Value;

/// Chat completions — `POST /v1/chat/completions`.
pub struct Chat<'a> {
    pub(crate) client: &'a Client,
}

impl Chat<'_> {
    pub async fn create(&self, request: impl Serialize) -> Result<Value> {
        let body = with_stream(request, false)?;
        self.client
            .request_json(Method::POST, "/v1/chat/completions", "api_key", Some(body))
            .await
    }

    pub async fn create_stream(
        &self,
        request: impl Serialize,
    ) -> Result<impl Stream<Item = Result<Value>>> {
        let body = with_stream(request, true)?;
        let resp = self
            .client
            .open_stream(Method::POST, "/v1/chat/completions", "api_key", Some(body))
            .await?;
        Ok(parse_sse(resp))
    }
}

/// Anthropic-compatible messages — `POST /v1/messages`.
pub struct Messages<'a> {
    pub(crate) client: &'a Client,
}

impl Messages<'_> {
    pub async fn create(&self, request: impl Serialize) -> Result<Value> {
        let body = with_stream(request, false)?;
        self.client
            .request_json(Method::POST, "/v1/messages", "api_key", Some(body))
            .await
    }

    pub async fn create_stream(
        &self,
        request: impl Serialize,
    ) -> Result<impl Stream<Item = Result<Value>>> {
        let body = with_stream(request, true)?;
        let resp = self
            .client
            .open_stream(Method::POST, "/v1/messages", "api_key", Some(body))
            .await?;
        Ok(parse_sse(resp))
    }

    pub async fn count_tokens(&self, request: impl Serialize) -> Result<Value> {
        let body = serde_json::to_value(request)?;
        self.client
            .request_json(
                Method::POST,
                "/v1/messages/count_tokens",
                "api_key",
                Some(body),
            )
            .await
    }
}

/// OpenAI Responses API — `POST /v1/responses`.
pub struct Responses<'a> {
    pub(crate) client: &'a Client,
}

impl Responses<'_> {
    pub async fn create(&self, request: impl Serialize) -> Result<Value> {
        let body = with_stream(request, false)?;
        self.client
            .request_json(Method::POST, "/v1/responses", "api_key", Some(body))
            .await
    }

    pub async fn create_stream(
        &self,
        request: impl Serialize,
    ) -> Result<impl Stream<Item = Result<Value>>> {
        let body = with_stream(request, true)?;
        let resp = self
            .client
            .open_stream(Method::POST, "/v1/responses", "api_key", Some(body))
            .await?;
        Ok(parse_sse(resp))
    }
}

/// Google Gemini-compatible generation — `POST /v1beta/models/{model}:{method}`.
pub struct Gemini<'a> {
    pub(crate) client: &'a Client,
}

impl Gemini<'_> {
    pub async fn generate_content(&self, model: &str, request: impl Serialize) -> Result<Value> {
        let body = serde_json::to_value(request)?;
        let path = format!("/v1beta/models/{}:generateContent", enc(model));
        self.client
            .request_json(Method::POST, &path, "api_key", Some(body))
            .await
    }

    pub async fn stream_generate_content(
        &self,
        model: &str,
        request: impl Serialize,
    ) -> Result<impl Stream<Item = Result<Value>>> {
        let body = serde_json::to_value(request)?;
        let path = format!("/v1beta/models/{}:streamGenerateContent", enc(model));
        let resp = self
            .client
            .open_stream(Method::POST, &path, "api_key", Some(body))
            .await?;
        Ok(parse_sse(resp))
    }
}
