"""
パイプライン全体を API 越しに検証する統合テスト。
外部依存（HuggingFace, Blender, Homestyler）は monkeypatch でモックする。
"""

import pytest
from fastapi.testclient import TestClient

import main
from routers import process as process_module


@pytest.fixture
def client():
    return TestClient(main.app)


def test_health_endpoint(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_health_detail_endpoint(client):
    r = client.get("/health/detail")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] in ("ok", "degraded")
    assert set(body["components"].keys()) == {"blender", "model_provider", "homestyler"}
    for c in body["components"].values():
        assert "ok" in c and "detail" in c


def test_process_rejects_empty_images(client):
    r = client.post(
        "/api/process",
        json={
            "product_name": "x",
            "source_url": "https://example.com/p",
            "site": "x",
            "dimensions": {},
            "colors": [],
            "materials": [],
            "images": [],
        },
    )
    # Pydantic (images min_length=1) → 422
    assert r.status_code == 422


def test_status_returns_404_for_unknown_id(client):
    r = client.get("/api/status/missing")
    assert r.status_code == 404


def _poll_until_terminal(client, job_id: str, timeout: float = 5.0) -> dict:
    import time

    deadline = time.time() + timeout
    while time.time() < deadline:
        r = client.get(f"/api/status/{job_id}")
        assert r.status_code == 200
        body = r.json()
        if body["status"] in ("success", "error"):
            return body
        time.sleep(0.05)
    raise AssertionError(f"ジョブが {timeout}s 以内に終了しませんでした")


def test_full_pipeline_success(client, monkeypatch):
    """全サービスをモックして、queued → success の流れを検証"""

    async def fake_download(images):
        return "output/fake_input.jpg"

    async def fake_generate(image_path):
        assert image_path == "output/fake_input.jpg"
        return "output/fake_raw.glb"

    def fake_scale(glb_path, w, d, h):
        assert (w, d, h) == (80.0, 40.0, 75.0)
        return glb_path.replace("_raw.glb", "_scaled.glb")

    upload_calls = []

    async def fake_upload(glb_path, product_name, dimensions, category):
        upload_calls.append((glb_path, product_name, dimensions, category))

    monkeypatch.setattr(process_module, "download_main_image", fake_download)
    monkeypatch.setattr(process_module, "generate_3d_model", fake_generate)
    monkeypatch.setattr(process_module, "apply_real_scale", fake_scale)
    monkeypatch.setattr(process_module, "upload_to_homestyler", fake_upload)

    payload = {
        "product_name": "テストチェア",
        "source_url": "http://example.com/x",
        "site": "test",
        "dimensions": {"width_cm": 80, "depth_cm": 40, "height_cm": 75},
        "colors": [],
        "materials": [],
        "images": [{"url": "https://example.com/x.jpg", "type": "front"}],
        "category": "椅子",
    }
    r = client.post("/api/process", json=payload)
    assert r.status_code == 202
    job_id = r.json()["job_id"]

    final = _poll_until_terminal(client, job_id)
    assert final["status"] == "success"
    assert final["step"] == "done"
    assert final["step_index"] == final["total_steps"]
    assert final["result"]["product"] == "テストチェア"
    assert final["result"]["glb"].endswith("_scaled.glb")
    # Homestyler 呼び出しが正しい引数で行われた
    assert len(upload_calls) == 1
    glb, name, dims, cat = upload_calls[0]
    assert glb == "output/fake_scaled.glb"
    assert name == "テストチェア"
    assert dims == {"width_cm": 80, "depth_cm": 40, "height_cm": 75}
    assert cat == "椅子"


def test_list_jobs_endpoint(client, monkeypatch):
    """ジョブ履歴 API が最新順で返ることを確認"""

    # 既存ジョブの影響を避けるため、まず POST → 結果を確認
    async def fake_download(images):
        return "output/fake.jpg"

    async def fake_generate(p):
        return "output/fake_raw.glb"

    def fake_scale(p, w, d, h):
        return p.replace("_raw.glb", "_scaled.glb")

    async def fake_upload(**kw):
        pass

    monkeypatch.setattr(process_module, "download_main_image", fake_download)
    monkeypatch.setattr(process_module, "generate_3d_model", fake_generate)
    monkeypatch.setattr(process_module, "apply_real_scale", fake_scale)
    monkeypatch.setattr(process_module, "upload_to_homestyler", fake_upload)

    payload = {
        "product_name": "リスト用テスト",
        "source_url": "http://x",
        "site": "x",
        "dimensions": {"width_cm": 1, "depth_cm": 1, "height_cm": 1},
        "colors": [],
        "materials": [],
        "images": [{"url": "https://example.com/x.jpg", "type": "front"}],
    }
    r = client.post("/api/process", json=payload)
    job_id = r.json()["job_id"]
    _poll_until_terminal(client, job_id)

    r = client.get("/api/jobs?limit=10")
    assert r.status_code == 200
    body = r.json()
    assert "jobs" in body and "count" in body
    assert body["count"] >= 1
    # 作ったジョブが含まれている
    assert any(j["id"] == job_id for j in body["jobs"])
    # 最新順 (created_at desc)
    timestamps = [j["created_at"] for j in body["jobs"]]
    assert timestamps == sorted(timestamps, reverse=True)


def test_list_jobs_rejects_bad_limit(client):
    assert client.get("/api/jobs?limit=0").status_code == 400
    assert client.get("/api/jobs?limit=10000").status_code == 400


def test_full_pipeline_propagates_error(client, monkeypatch):
    """3D生成で失敗 → ジョブが error 状態になる"""

    async def fake_download(images):
        return "output/fake_input.jpg"

    async def fake_generate(image_path):
        raise RuntimeError("HF API rate limited")

    monkeypatch.setattr(process_module, "download_main_image", fake_download)
    monkeypatch.setattr(process_module, "generate_3d_model", fake_generate)

    r = client.post(
        "/api/process",
        json={
            "product_name": "p",
            "source_url": "http://x",
            "site": "x",
            "dimensions": {"width_cm": 1, "depth_cm": 1, "height_cm": 1},
            "colors": [],
            "materials": [],
            "images": [{"url": "https://example.com/x.jpg", "type": "front"}],
        },
    )
    job_id = r.json()["job_id"]

    final = _poll_until_terminal(client, job_id)
    assert final["status"] == "error"
    assert "HF API rate limited" in final["error"]
    # スケール補正に到達せずに止まる
    assert final["step"] == "generating_3d"
