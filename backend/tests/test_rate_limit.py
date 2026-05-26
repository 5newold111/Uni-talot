"""
TokenBucket と RateLimitMiddleware の動作検証。
"""

import importlib
import time

import pytest
from fastapi.testclient import TestClient

from services.rate_limit import TokenBucket


def test_bucket_starts_full():
    b = TokenBucket(capacity=5, refill_per_sec=1.0)
    for _ in range(5):
        assert b.consume("ip1") is True
    assert b.consume("ip1") is False


def test_bucket_refills_over_time():
    b = TokenBucket(capacity=2, refill_per_sec=100.0)  # 100/sec
    assert b.consume("ip1") and b.consume("ip1")
    assert b.consume("ip1") is False
    # 0.05s 待つと最低 1 つトークンが戻る
    time.sleep(0.05)
    assert b.consume("ip1") is True


def test_bucket_separates_keys():
    b = TokenBucket(capacity=1, refill_per_sec=0.0)
    assert b.consume("ip1") is True
    assert b.consume("ip1") is False
    # 別の IP は影響を受けない
    assert b.consume("ip2") is True


@pytest.fixture
def limited_client(monkeypatch):
    # 容量 2、リフィル 0 のキツい設定でテスト
    monkeypatch.setenv("RATE_LIMIT_BURST", "2")
    monkeypatch.setenv("RATE_LIMIT_PER_SEC", "0")
    import main

    importlib.reload(main)
    return TestClient(main.app)


PAYLOAD = {
    "product_name": "rate-test",
    "source_url": "https://example.com/p",
    "site": "example.com",
    "dimensions": {"width_cm": 10, "depth_cm": 10, "height_cm": 10},
    "colors": [],
    "materials": [],
    "images": [{"url": "https://example.com/x.jpg", "type": "front"}],
}


def test_third_request_is_rate_limited(limited_client):
    r1 = limited_client.post("/api/process", json=PAYLOAD)
    r2 = limited_client.post("/api/process", json=PAYLOAD)
    r3 = limited_client.post("/api/process", json=PAYLOAD)
    assert r1.status_code == 202
    assert r2.status_code == 202
    assert r3.status_code == 429
    assert r3.headers.get("retry-after") == "2"


def test_get_endpoints_not_rate_limited(limited_client):
    # GET は対象外
    for _ in range(10):
        assert limited_client.get("/api/jobs").status_code == 200


def test_health_not_rate_limited(limited_client):
    for _ in range(10):
        assert limited_client.get("/health").status_code == 200
