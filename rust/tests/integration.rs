use airforce::{Client, Error};
use futures::StreamExt;
use serde_json::json;
use wiremock::matchers::{header, method, path};
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
