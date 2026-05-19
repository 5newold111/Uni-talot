"""
CORS が Chrome 拡張機能 + localhost のみ許可することを検証する。
"""

import pytest
from fastapi.testclient import TestClient

import main


@pytest.fixture
def client():
    return TestClient(main.app)


@pytest.mark.parametrize(
    "origin",
    [
        "chrome-extension://abcdefghijklmnopabcdefghijklmnop",
        "http://localhost:3000",
        "http://localhost",
        "http://127.0.0.1:3000",
        "https://localhost:3000",
    ],
)
def test_allowed_origins_get_cors_header(client, origin):
    r = client.get("/health", headers={"Origin": origin})
    assert r.status_code == 200
    # 許可された場合、Access-Control-Allow-Origin にエコーバックされる
    assert r.headers.get("access-control-allow-origin") == origin


@pytest.mark.parametrize(
    "origin",
    [
        "https://evil.example.com",
        "http://attacker.local",
        "https://nitori-net.jp",
        "chrome-extension://",  # 空ID
        "file:///tmp/x.html",
    ],
)
def test_disallowed_origins_have_no_cors_header(client, origin):
    r = client.get("/health", headers={"Origin": origin})
    assert r.status_code == 200
    # 拒否された場合 Access-Control-Allow-Origin は返らない
    assert "access-control-allow-origin" not in {k.lower() for k in r.headers}


def test_preflight_allowed_for_extension(client):
    r = client.options(
        "/api/process",
        headers={
            "Origin": "chrome-extension://abcdef0123",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == "chrome-extension://abcdef0123"
    assert "POST" in r.headers.get("access-control-allow-methods", "")


def test_preflight_denied_for_unrelated_site(client):
    r = client.options(
        "/api/process",
        headers={
            "Origin": "https://evil.example.com",
            "Access-Control-Request-Method": "POST",
        },
    )
    # Starlette は許可されない preflight に 400 を返す
    assert r.status_code == 400
