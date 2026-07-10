from __future__ import annotations

import json

import httpx
import pytest

from airforce import Airforce, AsyncAirforce, MissingCredentialError

EMBEDDING_RESPONSE = {
    "object": "list",
    "data": [{"object": "embedding", "index": 0, "embedding": [0.1, 0.2, 0.3]}],
    "model": "embed-1",
    "usage": {"prompt_tokens": 2, "total_tokens": 2},
}


def client_with(handler, **kwargs) -> Airforce:
    return Airforce(http_client=httpx.Client(transport=httpx.MockTransport(handler)), **kwargs)


# --- Embeddings ----------------------------------------------------------------

def test_embeddings_create_sends_body_and_parses_response():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("authorization")
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json=EMBEDDING_RESPONSE)

    client = client_with(handler, api_key="sk-air-test")
    res = client.embeddings.create(model="embed-1", input=["hello", "world"], dimensions=64)
    assert seen["url"] == "https://api.airforce/v1/embeddings"
    assert seen["auth"] == "Bearer sk-air-test"
    assert seen["body"] == {"model": "embed-1", "input": ["hello", "world"], "dimensions": 64}
    assert res["data"][0]["embedding"] == [0.1, 0.2, 0.3]
    assert res["usage"]["prompt_tokens"] == 2


async def test_async_embeddings_create():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=EMBEDDING_RESPONSE)

    client = AsyncAirforce(api_key="sk-air-test", http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    res = await client.embeddings.create(model="embed-1", input="hello")
    assert res["object"] == "list"
    await client.aclose()


# --- Organizations ---------------------------------------------------------------

def test_org_members_list_unwraps_and_uses_session_token():
    seen = {}
    members = [{"user_id": "u1", "role": "owner", "status": "active", "joined_at": 0}]

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("authorization")
        return httpx.Response(200, json={"members": members})

    client = client_with(handler, session_token="jwt-1")
    assert client.org.members() == members
    assert seen["url"] == "https://api.airforce/api/org/members"
    assert seen["auth"] == "Bearer jwt-1"


def test_org_requires_session_token():
    client = client_with(lambda r: httpx.Response(200, json={}), api_key="sk-air-test")
    with pytest.raises(MissingCredentialError):
        client.org.get()


def test_org_usage_maps_from_param():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["params"] = dict(request.url.params)
        return httpx.Response(200, json={"total": {"requests": 0}})

    client = client_with(handler, session_token="jwt-1")
    client.org.usage(from_=100, to=200, key_id="okey_1")
    assert seen["params"] == {"from": "100", "to": "200", "key_id": "okey_1"}


def test_org_create_key_posts_member_id():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["url"] = str(request.url)
        seen["body"] = json.loads(request.content)
        return httpx.Response(201, json={"item": {"id": "okey_1", "key": "sk-air-full"}})

    client = client_with(handler, session_token="jwt-1")
    res = client.org.create_key(member_user_id="u2", label="ci", rpm_limit=60)
    assert seen["method"] == "POST"
    assert seen["url"] == "https://api.airforce/api/org/keys"
    assert seen["body"] == {"member_user_id": "u2", "label": "ci", "rpm_limit": 60}
    assert res["item"]["id"] == "okey_1"


# --- Notifications ---------------------------------------------------------------

def test_notifications_list_sends_cursor_params():
    seen = {}
    feed = {"items": [{"id": "n1", "kind": "price_drop", "created_at": 10}], "unread": 1}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("authorization")
        return httpx.Response(200, json=feed)

    client = client_with(handler, session_token="jwt-1")
    res = client.notifications.list(limit=10, before="10")
    assert seen["url"] == "https://api.airforce/api/me/notifications?limit=10&before=10"
    assert seen["auth"] == "Bearer jwt-1"
    assert res == feed


def test_notifications_update_prefs_preserves_explicit_null():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"quiet_hours": None})

    client = client_with(handler, session_token="jwt-1")
    client.notifications.update_prefs({"quiet_hours": None, "digest_frequency": "daily"})
    # quiet_hours: null must reach the server verbatim (it clears the setting).
    assert seen["body"] == {"quiet_hours": None, "digest_frequency": "daily"}


def test_notifications_mark_all_read():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"updated": 3, "unread": 0})

    client = client_with(handler, session_token="jwt-1")
    res = client.notifications.mark_read(mark_all=True)
    assert seen["url"] == "https://api.airforce/api/me/notifications/read"
    assert seen["body"] == {"all": True}
    assert res["unread"] == 0


def test_link_channel_allows_empty_address_for_bots():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"status": "link_ready", "channel": "telegram", "code": "123456", "expires_minutes": 30})

    client = client_with(handler, session_token="jwt-1")
    res = client.notifications.link_channel(channel="telegram")
    assert seen["body"] == {"channel": "telegram", "address": ""}
    assert res["status"] == "link_ready"


# --- Account closure -------------------------------------------------------------

def test_delete_account_sends_reauth_body():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("authorization")
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"closed": True})

    client = client_with(handler, session_token="jwt-1")
    res = client.account.delete_account(password="pw", forfeit_balance_ack=True)
    assert seen["method"] == "DELETE"
    assert seen["url"] == "https://api.airforce/api/me/account"
    assert seen["auth"] == "Bearer jwt-1"
    assert seen["body"] == {"password": "pw", "forfeit_balance_ack": True}
    assert res == {"closed": True}


def test_reactivate_is_public():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("authorization")
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"reactivated": True, "email_restored": True, "username_restored": True})

    client = client_with(handler)  # no credentials at all
    res = client.account.reactivate(email="old@example.com", password="pw")
    assert seen["url"] == "https://api.airforce/auth/reactivate"
    assert seen["auth"] is None
    assert seen["body"] == {"email": "old@example.com", "password": "pw"}
    assert res["reactivated"] is True


# --- 3D generation ---------------------------------------------------------------

def test_threed_generate_poll_and_download():
    seen = {"paths": []}
    task = {"task_id": "t3d_1", "status": "queued", "model": "shape-1", "created": 0,
            "expires_at": 9999, "has_result": False}
    done = {**task, "status": "completed", "has_result": True, "format": "glb"}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["paths"].append(f"{request.method} {request.url.path}")
        if request.method == "POST":
            seen["body"] = json.loads(request.content)
            return httpx.Response(200, json=task)
        if request.url.path.endswith("/content"):
            return httpx.Response(200, headers={"content-type": "model/gltf-binary"}, content=b"glTF-bytes")
        return httpx.Response(200, json=done)

    client = client_with(handler, api_key="sk-air-test")
    created = client.three_d.generate(model="shape-1", image_urls=["https://example.com/a.png"], resolution="high")
    assert created["task_id"] == "t3d_1"
    assert seen["body"] == {"model": "shape-1", "image_urls": ["https://example.com/a.png"], "resolution": "high"}

    finished = client.three_d.wait_for_completion("t3d_1", poll_interval=0)
    assert finished["status"] == "completed"

    blob = client.three_d.content("t3d_1")
    assert blob == b"glTF-bytes"
    assert seen["paths"] == [
        "POST /v1/3d/generations",
        "GET /v1/3d/tasks/t3d_1",
        "GET /v1/3d/tasks/t3d_1/content",
    ]


# --- Account routing preferences ---------------------------------------------------

def test_channel_order_prefs_put_verbatim_with_api_key():
    seen = {}
    prefs = {"gpt-5.4": {"order": ["a", "b"], "auto_fallback": True}}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("authorization")
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"success": True})

    client = client_with(handler, api_key="sk-air-test")
    client.account.set_channel_order_prefs(prefs)
    assert seen["method"] == "PUT"
    assert seen["url"] == "https://api.airforce/api/user/channel-order-prefs"
    assert seen["auth"] == "Bearer sk-air-test"
    assert seen["body"] == prefs


def test_custom_model_crud_paths():
    seen = {"calls": []}

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content) if request.content else None
        seen["calls"].append((request.method, request.url.path, body))
        return httpx.Response(200, json={"success": True})

    client = client_with(handler, session_token="jwt-1")
    client.account.create_custom_model(fake_name="my-model", endpoint="https://api.example.com/v1", api_key="secret")
    client.account.update_custom_model("my-model", endpoint="https://api2.example.com/v1")
    client.account.delete_custom_model("my-model")
    assert seen["calls"] == [
        ("POST", "/api/models", {"fake_name": "my-model", "endpoint": "https://api.example.com/v1", "api_key": "secret"}),
        ("PUT", "/api/models/my-model", {"endpoint": "https://api2.example.com/v1"}),
        ("DELETE", "/api/models/my-model", None),
    ]
