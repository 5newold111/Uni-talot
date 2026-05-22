"""
v2.0 で導入された切り離し版 Homestyler アップロードエンドポイントの検証。

`POST /api/jobs/{job_id}/upload-to-homestyler` は GLB 生成成功後の
オプショナル後処理として呼ばれる。Homestyler が壊れていてもコアジョブの
result (GLB パス) は保持される、というのが v2.0 の設計上の利点。
"""

import time

import pytest
from fastapi.testclient import TestClient

import main
from routers import process as process_module
from services.errors import ErrorCode, PipelineError


@pytest.fixture
def client():
    return TestClient(main.app)


PAYLOAD = {
    "product_name": "test-table",
    "source_url": "https://example.com/p",
    "site": "example.com",
    "dimensions": {"width_cm": 80, "depth_cm": 40, "height_cm": 75},
    "colors": [],
    "materials": [],
    "images": [{"url": "https://example.com/x.jpg", "type": "front"}],
    "category": "テーブル",
}


def _setup_successful_job(client, monkeypatch) -> str:
    """コアパイプラインを成功させてジョブIDを返す"""

    async def fake_download(images):
        return "output/test.jpg"

    async def fake_generate(p):
        return "output/test_raw.glb"

    def fake_scale(p, w, d, h):
        return p.replace("_raw.glb", "_scaled.glb")

    monkeypatch.setattr(process_module, "download_main_image", fake_download)
    monkeypatch.setattr(process_module, "generate_3d_model", fake_generate)
    monkeypatch.setattr(process_module, "apply_real_scale", fake_scale)

    r = client.post("/api/process", json=PAYLOAD)
    job_id = r.json()["job_id"]

    deadline = time.time() + 3.0
    while time.time() < deadline:
        body = client.get(f"/api/status/{job_id}").json()
        if body["status"] == "success":
            break
        time.sleep(0.05)
    assert body["status"] == "success"
    return job_id


def test_upload_to_homestyler_404_for_unknown_job(client):
    r = client.post("/api/jobs/missing/upload-to-homestyler")
    assert r.status_code == 404


def test_upload_to_homestyler_409_when_no_glb(client, monkeypatch):
    """GLB が無い (生成中 or 失敗) ジョブに対しては 409 を返す"""
    from services.job_manager import jobs as global_jobs

    async def make_pending():
        return await global_jobs.create("pending-job")

    import asyncio

    job = asyncio.run(make_pending())
    r = client.post(f"/api/jobs/{job.id}/upload-to-homestyler")
    assert r.status_code == 409
    assert "GLB" in r.json()["detail"]


def test_upload_to_homestyler_uses_stored_result(client, monkeypatch):
    """成功ジョブの result に保存された GLB / dimensions / category で upload が呼ばれる"""
    job_id = _setup_successful_job(client, monkeypatch)

    captured = {}

    async def fake_upload(*, glb_path, product_name, dimensions, category):
        captured["glb_path"] = glb_path
        captured["product_name"] = product_name
        captured["dimensions"] = dimensions
        captured["category"] = category

    monkeypatch.setattr(process_module, "upload_to_homestyler", fake_upload)

    r = client.post(f"/api/jobs/{job_id}/upload-to-homestyler")
    assert r.status_code == 202

    deadline = time.time() + 3.0
    while time.time() < deadline:
        body = client.get(f"/api/status/{job_id}").json()
        if body["status"] in ("success", "error") and body["step"] == "done":
            break
        time.sleep(0.05)

    assert captured["glb_path"].endswith("_scaled.glb")
    assert captured["product_name"] == "test-table"
    assert captured["dimensions"] == {"width_cm": 80, "depth_cm": 40, "height_cm": 75}
    assert captured["category"] == "テーブル"


def test_upload_to_homestyler_failure_preserves_glb_in_result(client, monkeypatch):
    """Homestyler 後処理が失敗してもジョブの result (GLB) は失われない"""
    job_id = _setup_successful_job(client, monkeypatch)

    # 成功直後の result を覚える
    before = client.get(f"/api/status/{job_id}").json()
    assert before["result"]["glb"].endswith("_scaled.glb")

    async def fake_upload_fails(**kwargs):
        raise PipelineError(ErrorCode.HOMESTYLER_UI_CHANGED, "selectors mismatch")

    monkeypatch.setattr(process_module, "upload_to_homestyler", fake_upload_fails)

    r = client.post(f"/api/jobs/{job_id}/upload-to-homestyler")
    assert r.status_code == 202

    deadline = time.time() + 3.0
    while time.time() < deadline:
        body = client.get(f"/api/status/{job_id}").json()
        if body["status"] == "error":
            break
        time.sleep(0.05)

    assert body["status"] == "error"
    assert body["error_code"] == "homestyler_ui_changed"
    # 重要: GLB の result は消えていない (再アップロード可能)
    assert body["result"] is not None
    assert body["result"]["glb"].endswith("_scaled.glb")


def test_core_pipeline_no_longer_calls_homestyler(client, monkeypatch):
    """v2.0 動作確認: /api/process は Homestyler を呼ばない"""
    call_count = 0

    async def must_not_be_called(**kwargs):
        nonlocal call_count
        call_count += 1

    async def fake_download(images):
        return "output/x.jpg"

    async def fake_generate(p):
        return "output/x_raw.glb"

    def fake_scale(p, w, d, h):
        return p.replace("_raw.glb", "_scaled.glb")

    monkeypatch.setattr(process_module, "download_main_image", fake_download)
    monkeypatch.setattr(process_module, "generate_3d_model", fake_generate)
    monkeypatch.setattr(process_module, "apply_real_scale", fake_scale)
    monkeypatch.setattr(process_module, "upload_to_homestyler", must_not_be_called)

    r = client.post("/api/process", json=PAYLOAD)
    job_id = r.json()["job_id"]

    deadline = time.time() + 3.0
    while time.time() < deadline:
        body = client.get(f"/api/status/{job_id}").json()
        if body["status"] == "success":
            break
        time.sleep(0.05)

    assert body["status"] == "success"
    assert body["total_steps"] == 3  # 4 → 3 に削減
    assert call_count == 0  # 自動アップロード無し
