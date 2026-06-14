use super::enc;
use crate::client::Client;
use crate::error::Result;
use serde_json::Value;

/// Model catalog / discovery.
pub struct Models<'a> {
    pub(crate) client: &'a Client,
}

impl Models<'_> {
    /// List public models (returns the `data` array).
    pub async fn list(&self, channels: bool) -> Result<Value> {
        let query = if channels {
            Some(vec![("channels".to_string(), "1".to_string())])
        } else {
            None
        };
        let res = self
            .client
            .get_json("/v1/models", "none", query.as_deref())
            .await?;
        Ok(res.get("data").cloned().unwrap_or(res))
    }

    pub async fn detail(&self, model: &str) -> Result<Value> {
        self.client
            .get_json(&format!("/api/models/{}/detail", enc(model)), "none", None)
            .await
    }

    pub async fn allowed_params(&self, model: &str) -> Result<Value> {
        self.client
            .get_json(
                &format!("/api/models/{}/allowed-params", enc(model)),
                "none",
                None,
            )
            .await
    }

    pub async fn classes(&self) -> Result<Value> {
        self.client
            .get_json("/v1/playground/model-classes", "none", None)
            .await
    }
}
