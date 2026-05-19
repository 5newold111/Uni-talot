"""
ProductData の Pydantic バリデーション検証。
"""

import pytest
from fastapi.testclient import TestClient

import main


@pytest.fixture
def client():
    return TestClient(main.app)


VALID_PAYLOAD = {
    "product_name": "テスト商品",
    "source_url": "https://example.com/p/1",
    "site": "example.com",
    "dimensions": {"width_cm": 80, "depth_cm": 40, "height_cm": 75},
    "colors": [],
    "materials": [],
    "images": [{"url": "https://example.com/i.jpg", "type": "front"}],
}


def test_valid_payload_returns_202(client):
    r = client.post("/api/process", json=VALID_PAYLOAD)
    assert r.status_code == 202


def test_empty_product_name_rejected(client):
    payload = {**VALID_PAYLOAD, "product_name": ""}
    r = client.post("/api/process", json=payload)
    assert r.status_code == 422


def test_invalid_source_url_rejected(client):
    payload = {**VALID_PAYLOAD, "source_url": "not-a-url"}
    r = client.post("/api/process", json=payload)
    assert r.status_code == 422


def test_empty_images_rejected(client):
    payload = {**VALID_PAYLOAD, "images": []}
    r = client.post("/api/process", json=payload)
    assert r.status_code == 422


def test_invalid_image_url_rejected(client):
    payload = {**VALID_PAYLOAD, "images": [{"url": "javascript:alert(1)", "type": "front"}]}
    r = client.post("/api/process", json=payload)
    assert r.status_code == 422


def test_negative_dimension_rejected(client):
    payload = {**VALID_PAYLOAD, "dimensions": {"width_cm": -1, "depth_cm": 40, "height_cm": 75}}
    r = client.post("/api/process", json=payload)
    assert r.status_code == 422


def test_huge_dimension_rejected(client):
    payload = {**VALID_PAYLOAD, "dimensions": {"width_cm": 99999, "depth_cm": 40, "height_cm": 75}}
    r = client.post("/api/process", json=payload)
    assert r.status_code == 422


def test_too_many_images_rejected(client):
    payload = {
        **VALID_PAYLOAD,
        "images": [{"url": f"https://example.com/i{i}.jpg", "type": "other"} for i in range(51)],
    }
    r = client.post("/api/process", json=payload)
    assert r.status_code == 422


def test_zero_dimensions_accepted(client):
    """寸法 0 はバリデーション通過 (scale_correction でスキップされる挙動)"""
    payload = {**VALID_PAYLOAD, "dimensions": {}}
    r = client.post("/api/process", json=payload)
    assert r.status_code == 202


def test_errors_guidance_endpoint(client):
    r = client.get("/api/errors/guidance")
    assert r.status_code == 200
    body = r.json()
    assert "guidance" in body
    assert "image_download_failed" in body["guidance"]
    assert "model_quota_exceeded" in body["guidance"]
