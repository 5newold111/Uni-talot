"""
X-API-Key 認証ミドルウェアの動作検証。
"""

import importlib

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def authed_client(monkeypatch):
    """EC3D_API_KEY を設定してアプリを再ロード"""
    monkeypatch.setenv("EC3D_API_KEY", "secret-token-xyz")
    import main

    importlib.reload(main)
    yield TestClient(main.app)
    # cleanup: env を戻して main を reload
    monkeypatch.delenv("EC3D_API_KEY", raising=False)
    importlib.reload(main)


@pytest.fixture
def open_client(monkeypatch):
    """EC3D_API_KEY を空にしてアプリを再ロード"""
    monkeypatch.setenv("EC3D_API_KEY", "")
    import main

    importlib.reload(main)
    return TestClient(main.app)


def test_health_is_always_public(authed_client):
    assert authed_client.get("/health").status_code == 200
    assert authed_client.get("/health/detail").status_code == 200


def test_protected_endpoint_requires_key(authed_client):
    r = authed_client.get("/api/jobs")
    assert r.status_code == 401
    assert "Invalid or missing" in r.json()["detail"]


def test_correct_key_allows_access(authed_client):
    r = authed_client.get("/api/jobs", headers={"X-API-Key": "secret-token-xyz"})
    assert r.status_code == 200


def test_wrong_key_rejected(authed_client):
    r = authed_client.get("/api/jobs", headers={"X-API-Key": "wrong-token"})
    assert r.status_code == 401


def test_disabled_auth_allows_all(open_client):
    r = open_client.get("/api/jobs")
    assert r.status_code == 200
