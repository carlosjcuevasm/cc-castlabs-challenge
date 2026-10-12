import httpx
import jwt
import pytest
from fastapi.testclient import TestClient

from app.main import app


TEST_SECRET_HEX = "a1" * 64


class FakeUpstream:
    def __init__(self):
        self.calls = []
        self.error = None
        self.response = httpx.Response(
            201,
            content=b'{"result":"forwarded"}',
            headers={"content-type": "application/json"},
        )

    async def post(self, url, **kwargs):
        self.calls.append({"url": url, **kwargs})

        if self.error:
            raise self.error

        return self.response


@pytest.fixture
def proxy_client(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_HEX", TEST_SECRET_HEX)
    monkeypatch.setenv("UPSTREAM_URL", "https://upstream.test/endpoint")

    with TestClient(app) as client:
        upstream = FakeUpstream()
        app.state.http_client = upstream
        yield client, upstream


def test_proxy_forwards_body_and_jwt(proxy_client):
    client, upstream = proxy_client
    body = {"username": "alice", "extra": {"role": "admin"}}

    response = client.post("/proxy", json=body)

    assert response.status_code == 201
    assert upstream.calls[0]["url"] == "https://upstream.test/endpoint"
    assert upstream.calls[0]["content"] == response.request.content

    forwarded_body = upstream.calls[0]["content"]
    assert forwarded_body == response.request.content

    headers = upstream.calls[0]["headers"]
    assert headers["content-type"] == "application/json"
    assert "x-my-jwt" in headers

    claims = jwt.decode(
        headers["x-my-jwt"],
        bytes.fromhex(TEST_SECRET_HEX),
        algorithms=["HS512"],
    )
    assert claims["payload"]["user"] == "alice"
    assert claims["payload"]["date"]
    assert claims["jti"]
    assert claims["iat"] > 0


def test_proxy_preserves_upstream_response(proxy_client):
    client, upstream = proxy_client
    upstream.response = httpx.Response(
        202,
        content=b'{"accepted":true}',
        headers={"content-type": "application/json"},
    )

    response = client.post("/proxy", json={"username": "alice"})

    assert response.status_code == 202
    assert response.content == b'{"accepted":true}'
    assert response.headers["content-type"] == "application/json"


def test_proxy_returns_502_when_upstream_fails(proxy_client):
    client, upstream = proxy_client
    upstream.error = httpx.ConnectError(
        "Connection failed",
        request=httpx.Request("POST", "https://upstream.test/endpoint"),
    )

    response = client.post("/proxy", json={"username": "alice"})

    assert response.status_code == 502
    assert response.json()["detail"] == "Unable to reach upstream endpoint"


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"username": ""},
        {"username": "   "},
    ],
)
def test_proxy_rejects_missing_or_blank_username(proxy_client, body):
    client, upstream = proxy_client

    response = client.post("/proxy", json=body)

    assert response.status_code == 422
    assert upstream.calls == []

def test_status_reports_uptime_and_proxy_request_count(proxy_client):
    client, upstream = proxy_client

    status = client.get("/status").json()

    assert status["uptime_seconds"] >= 0
    assert status["request_count"] == 0

    # Invalid requests count too.
    response = client.post("/proxy", json={})
    assert response.status_code == 422

    # Upstream failures also count.
    upstream.error = httpx.ConnectError(
        "Connection failed",
        request=httpx.Request("POST", "https://upstream.test/endpoint"),
    )
    response = client.post("/proxy", json={"username": "alice"})
    assert response.status_code == 502

    status = client.get("/status").json()

    assert status["request_count"] == 2
