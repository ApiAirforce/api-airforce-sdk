use airforce::{Client, Error};
use futures::StreamExt;
use serde_json::json;
use std::time::Duration;
use wiremock::matchers::{body_json, header, method, path, query_param};
use wiremock::{Mock, MockServer, ResponseTemplate};

const COMPLETION: &str = r#"{"id":"cmpl_1","object":"chat.completion","created":0,"model":"claude-opus-4.8","choices":[{"index":0,"message":{"role":"assistant","content":"hi"},"finish_reason":"stop"}]}"#;

fn json_response(status: u16, body: &str) -> ResponseTemplate {
    ResponseTemplate::new(status)
        .insert_header("content-type", "application/json")
        .set_body_string(body)
}

#[tokio::test]
async fn chat_create_sends_bearer_and_parses() {
    let server = MockServer::start().await;
    Mock::given(method("POST"))
        .and(path("/v1/chat/completions"))
        .and(header("authorization", "Bearer sk-air-test"))
        .respond_with(json_response(200, COMPLETION))
        .mount(&server)
        .await;

    let client = Client::builder()
        .api_key("sk-air-test")
        .base_url(server.uri())
        .build();
    let res = client
        .chat()
        .create(json!({"model":"claude-opus-4.8","messages":[]}))
        .await
        .unwrap();
    assert_eq!(res["choices"][0]["message"]["content"], "hi");
}

#[tokio::test]
async fn missing_api_key_errors() {
    let client = Client::builder().base_url("http://127.0.0.1:1").build();
    let err = client
        .chat()
        .create(json!({"model":"m","messages":[]}))
        .await
        .unwrap_err();
    assert!(matches!(err, Error::MissingCredential(_)));
}

#[tokio::test]
async fn session_endpoint_requires_session_token() {
    // Account.me is a session endpoint; an API key must NOT be substituted.
    let client = Client::builder()
        .api_key("sk-air-test")
        .base_url("http://127.0.0.1:1")
        .build();
    let err = client.account().me().await.unwrap_err();
    assert!(matches!(err, Error::MissingCredential(_)));
}

#[tokio::test]
async fn public_endpoint_has_no_auth() {
    let server = MockServer::start().await;
    Mock::given(method("GET"))
        .and(path("/v1/models"))
        .respond_with(json_response(200, r#"{"object":"list","data":[]}"#))
        .mount(&server)
        .await;

    let client = Client::builder()
        .api_key("sk-air-test")
        .base_url(server.uri())
        .build();
    client.models().list(false).await.unwrap();

    let requests = server.received_requests().await.unwrap();
    assert_eq!(requests.len(), 1);
    assert!(requests[0].headers.get("authorization").is_none());
}

#[tokio::test]
async fn retries_on_429_then_succeeds() {
    let server = MockServer::start().await;
    Mock::given(method("POST"))
        .and(path("/v1/chat/completions"))
        .respond_with(
            ResponseTemplate::new(429)
                .insert_header("retry-after", "0")
                .set_body_string("{\"error\":\"slow\"}"),
        )
        .up_to_n_times(1)
        .mount(&server)
        .await;
    Mock::given(method("POST"))
        .and(path("/v1/chat/completions"))
        .respond_with(json_response(200, COMPLETION))
        .mount(&server)
        .await;

    let client = Client::builder()
        .api_key("sk-air-test")
        .base_url(server.uri())
        .build();
    let res = client
        .chat()
        .create(json!({"model":"m","messages":[]}))
        .await
        .unwrap();
    assert_eq!(res["id"], "cmpl_1");
    assert_eq!(server.received_requests().await.unwrap().len(), 2);
}

#[tokio::test]
async fn error_mapping_payment_required() {
    let server = MockServer::start().await;
    Mock::given(method("POST"))
        .and(path("/v1/chat/completions"))
        .respond_with(json_response(
            402,
            r#"{"error":{"message":"no balance","code":"insufficient_balance"}}"#,
        ))
        .mount(&server)
        .await;

    let client = Client::builder()
        .api_key("sk-air-test")
        .base_url(server.uri())
        .build();
    let err = client
        .chat()
        .create(json!({"model":"m","messages":[]}))
        .await
        .unwrap_err();
    assert_eq!(err.status(), Some(402));
    assert!(err.is_insufficient_balance());
    assert_eq!(err.code(), Some("insufficient_balance"));
}

#[tokio::test]
async fn embeddings_create_sends_bearer_and_parses() {
    let server = MockServer::start().await;
    Mock::given(method("POST"))
        .and(path("/v1/embeddings"))
        .and(header("authorization", "Bearer sk-air-test"))
        .and(body_json(json!({"model": "text-embed-1", "input": "hello"})))
        .respond_with(json_response(
            200,
            r#"{"object":"list","data":[{"object":"embedding","index":0,"embedding":[0.1,0.2]}],"model":"text-embed-1","usage":{"prompt_tokens":2,"total_tokens":2}}"#,
        ))
        .mount(&server)
        .await;

    let client = Client::builder()
        .api_key("sk-air-test")
        .base_url(server.uri())
        .build();
    let res = client
        .embeddings()
        .create(json!({"model": "text-embed-1", "input": "hello"}))
        .await
        .unwrap();
    assert_eq!(res["object"], "list");
    assert_eq!(res["data"][0]["embedding"][1], 0.2);
    assert_eq!(res["usage"]["prompt_tokens"], 2);
}

#[tokio::test]
async fn org_members_lists_with_session_token() {
    let server = MockServer::start().await;
    Mock::given(method("GET"))
        .and(path("/api/org/members"))
        .and(header("authorization", "Bearer jwt-test"))
        .respond_with(json_response(
            200,
            r#"{"members":[{"user_id":"u1","role":"owner","status":"active","joined_at":0}]}"#,
        ))
        .mount(&server)
        .await;

    let client = Client::builder()
        .session_token("jwt-test")
        .base_url(server.uri())
        .build();
    let members = client.org().members().await.unwrap();
    assert_eq!(members[0]["user_id"], "u1");
    assert_eq!(members[0]["role"], "owner");
}

#[tokio::test]
async fn org_endpoint_requires_session_token() {
    // Org endpoints are session-authed; an API key must NOT be substituted.
    let client = Client::builder()
        .api_key("sk-air-test")
        .base_url("http://127.0.0.1:1")
        .build();
    let err = client.org().get().await.unwrap_err();
    assert!(matches!(err, Error::MissingCredential(_)));
}

#[tokio::test]
async fn notifications_list_passes_paging_query() {
    let server = MockServer::start().await;
    Mock::given(method("GET"))
        .and(path("/api/me/notifications"))
        .and(query_param("limit", "10"))
        .and(query_param("before", "1700000000"))
        .and(header("authorization", "Bearer jwt-test"))
        .respond_with(json_response(
            200,
            r#"{"items":[{"id":"n1","event_id":"e1","kind":"price_drop","params_json":"{}","created_at":1699999999}],"unread":1}"#,
        ))
        .mount(&server)
        .await;

    let client = Client::builder()
        .session_token("jwt-test")
        .base_url(server.uri())
        .build();
    let res = client
        .notifications()
        .list(Some(10), Some("1700000000"))
        .await
        .unwrap();
    assert_eq!(res["items"][0]["id"], "n1");
    assert_eq!(res["unread"], 1);
}

#[tokio::test]
async fn account_close_reauthenticates_in_body() {
    let server = MockServer::start().await;
    Mock::given(method("DELETE"))
        .and(path("/api/me/account"))
        .and(header("authorization", "Bearer jwt-test"))
        .and(body_json(json!({
            "password": "pw",
            "totp_code": "123456",
            "forfeit_balance_ack": true,
        })))
        .respond_with(json_response(200, r#"{"closed":true}"#))
        .mount(&server)
        .await;

    let client = Client::builder()
        .session_token("jwt-test")
        .base_url(server.uri())
        .build();
    let res = client
        .account()
        .close_account("pw", Some("123456"), true)
        .await
        .unwrap();
    assert_eq!(res["closed"], true);
}

#[tokio::test]
async fn threed_wait_then_download_content() {
    let server = MockServer::start().await;
    Mock::given(method("GET"))
        .and(path("/v1/3d/tasks/t3d_1"))
        .respond_with(json_response(
            200,
            r#"{"task_id":"t3d_1","status":"completed","model":"m","created":0,"expires_at":86400,"has_result":true,"format":"glb"}"#,
        ))
        .mount(&server)
        .await;
    Mock::given(method("GET"))
        .and(path("/v1/3d/tasks/t3d_1/content"))
        .respond_with(
            ResponseTemplate::new(200)
                .insert_header("content-type", "model/gltf-binary")
                .set_body_bytes(b"glTF-bytes".to_vec()),
        )
        .mount(&server)
        .await;

    let client = Client::builder()
        .api_key("sk-air-test")
        .base_url(server.uri())
        .build();
    let task = client
        .three_d()
        .wait_for_completion("t3d_1", Duration::from_millis(1), Duration::from_secs(5))
        .await
        .unwrap();
    assert_eq!(task["format"], "glb");
    let bytes = client.three_d().content("t3d_1").await.unwrap();
    assert_eq!(bytes, b"glTF-bytes");
}

#[tokio::test]
async fn streaming_assembles_content() {
    let sse = "data: {\"choices\":[{\"index\":0,\"delta\":{\"content\":\"he\"},\"finish_reason\":null}]}\n\n\
               data: {\"choices\":[{\"index\":0,\"delta\":{\"content\":\"llo\"},\"finish_reason\":\"stop\"}]}\n\n\
               data: [DONE]\n\n";
    let server = MockServer::start().await;
    Mock::given(method("POST"))
        .and(path("/v1/chat/completions"))
        .respond_with(
            ResponseTemplate::new(200)
                .insert_header("content-type", "text/event-stream")
                .set_body_string(sse),
        )
        .mount(&server)
        .await;

    let client = Client::builder()
        .api_key("sk-air-test")
        .base_url(server.uri())
        .build();
    let stream = client
        .chat()
        .create_stream(json!({"model":"m","messages":[]}))
        .await
        .unwrap();
    futures::pin_mut!(stream);

    let mut text = String::new();
    while let Some(chunk) = stream.next().await {
        let chunk = chunk.unwrap();
        if let Some(c) = chunk["choices"][0]["delta"]["content"].as_str() {
            text.push_str(c);
        }
    }
    assert_eq!(text, "hello");
}
