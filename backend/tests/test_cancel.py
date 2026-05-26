"""
ジョブキャンセル API の検証。
"""

import time

import pytest
from fastapi.testclient import TestClient

import main
from routers import process as process_module
from services.job_manager import JobManager


@pytest.fixture
def client():
    return TestClient(main.app)


PAYLOAD = {
    "product_name": "cancel-test",
    "source_url": "https://example.com/p",
    "site": "example.com",
    "dimensions": {"width_cm": 10, "depth_cm": 10, "height_cm": 10},
    "colors": [],
    "materials": [],
    "images": [{"url": "https://example.com/x.jpg", "type": "front"}],
}


def test_cancel_unknown_returns_404(client):
    r = client.post("/api/jobs/missing/cancel")
    assert r.status_code == 404


async def test_pipeline_aborts_when_cancel_flag_set(monkeypatch):
    """_run_pipeline を直接呼んで、開始前に cancel フラグが立っていれば
    最初の境界で abort し、後続ステップが呼ばれないことを確認する。"""
    from services.job_manager import jobs as global_jobs

    async def fake_download(images):
        pytest.fail("download は呼ばれてはいけない")

    async def fake_generate(p):
        pytest.fail("generate は呼ばれてはいけない")

    monkeypatch.setattr(process_module, "download_main_image", fake_download)
    monkeypatch.setattr(process_module, "generate_3d_model", fake_generate)

    job = await global_jobs.create("cancel-direct")
    await global_jobs.request_cancel(job.id)

    data = process_module.ProductData(**PAYLOAD)
    await process_module._run_pipeline(job.id, data)

    refreshed = await global_jobs.get(job.id)
    assert refreshed.status == "cancelled"
    assert bool(refreshed.cancel_requested) is True


async def test_pipeline_aborts_mid_flight_when_flag_set(monkeypatch):
    """download 中に cancel フラグが立てば、download 完了後の境界で abort し
    generate が呼ばれないことを確認する。"""
    from services.job_manager import jobs as global_jobs

    job = await global_jobs.create("cancel-mid")

    async def fake_download(images):
        # download 中にユーザーがキャンセルしたシナリオ
        await global_jobs.request_cancel(job.id)
        return "output/fake.jpg"

    async def fake_generate(p):
        pytest.fail("download 後の境界で abort されているはず")

    monkeypatch.setattr(process_module, "download_main_image", fake_download)
    monkeypatch.setattr(process_module, "generate_3d_model", fake_generate)

    data = process_module.ProductData(**PAYLOAD)
    await process_module._run_pipeline(job.id, data)

    refreshed = await global_jobs.get(job.id)
    assert refreshed.status == "cancelled"


def test_cancel_finished_job_rejected(client, monkeypatch):
    async def fake_dl(images):
        return "output/x.jpg"

    async def fake_gen(p):
        return "output/x_raw.glb"

    def fake_scale(p, w, d, h):
        return p.replace("_raw.glb", "_scaled.glb")

    async def fake_upload(**kw):
        return None

    monkeypatch.setattr(process_module, "download_main_image", fake_dl)
    monkeypatch.setattr(process_module, "generate_3d_model", fake_gen)
    monkeypatch.setattr(process_module, "apply_real_scale", fake_scale)
    monkeypatch.setattr(process_module, "upload_to_homestyler", fake_upload)

    r = client.post("/api/process", json=PAYLOAD)
    job_id = r.json()["job_id"]

    # 完了を待つ
    deadline = time.time() + 5.0
    while time.time() < deadline:
        body = client.get(f"/api/status/{job_id}").json()
        if body["status"] == "success":
            break
        time.sleep(0.05)

    # 完了後にキャンセル → 409
    cr = client.post(f"/api/jobs/{job_id}/cancel")
    assert cr.status_code == 409


async def test_request_cancel_returns_false_for_terminal(tmp_path):
    mgr = JobManager(db_path=str(tmp_path / "j.db"))
    j = await mgr.create("p")
    await mgr.update(j.id, status="success")
    assert (await mgr.request_cancel(j.id)) is False


async def test_request_cancel_returns_false_for_unknown(tmp_path):
    mgr = JobManager(db_path=str(tmp_path / "j.db"))
    assert (await mgr.request_cancel("nope")) is False


async def test_request_cancel_returns_true_for_running(tmp_path):
    mgr = JobManager(db_path=str(tmp_path / "j.db"))
    j = await mgr.create("p")
    await mgr.update(j.id, status="running", step="downloading_image")
    assert (await mgr.request_cancel(j.id)) is True
    refreshed = await mgr.get(j.id)
    assert bool(refreshed.cancel_requested) is True
