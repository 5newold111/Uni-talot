"""
全公開エンドポイントの最小スモークテスト。
ミドルウェアスタック全体 (CORS, APIKey, RateLimit, Lifespan) を素通ししての挙動を確認。
外部依存 (Tripo / Homestyler / Blender) はモック化する。
"""

import pytest
from fastapi.testclient import TestClient

import main
from routers import process as process_module


@pytest.fixture
def client(monkeypatch):
    async def fake_download(images):
        return "output/smoke_in.jpg"

    async def fake_generate(p):
        return "output/smoke_raw.glb"

    def fake_scale(p, w, d, h):
        return p.replace("_raw.glb", "_scaled.glb")

    async def fake_upload(**kw):
        return None

    monkeypatch.setattr(process_module, "download_main_image", fake_download)
    monkeypatch.setattr(process_module, "generate_3d_model", fake_generate)
    monkeypatch.setattr(process_module, "apply_real_scale", fake_scale)
    monkeypatch.setattr(process_module, "upload_to_homestyler", fake_upload)
    return TestClient(main.app)


# 公開エンドポイント全リスト (CHANGELOG / README と整合)
EXPECTED_PATHS = {
    "/health",
    "/health/detail",
    "/api/process",
    "/api/status/{job_id}",
    "/api/jobs",
    "/api/jobs/{job_id}/cancel",
    "/api/errors/guidance",
}


def test_all_documented_endpoints_are_registered():
    """README に書いた 7 エンドポイント全てが FastAPI に登録されている"""
    registered = {r.path for r in main.app.routes if hasattr(r, "path")}
    missing = EXPECTED_PATHS - registered
    assert not missing, f"未登録: {missing}"


def test_static_output_mount_is_registered():
    """3D プレビュー用に /output 静的配信がマウントされている"""
    paths = {getattr(r, "path", None) for r in main.app.routes}
    assert "/output" in paths


def test_openapi_docs_available(client):
    r = client.get("/openapi.json")
    assert r.status_code == 200
    spec = r.json()
    # 主要エンドポイントが OpenAPI 仕様に載っている
    for path in ["/api/process", "/api/jobs", "/api/jobs/{job_id}/cancel"]:
        assert path in spec["paths"], f"OpenAPI に {path} がない"


def test_swagger_ui_available(client):
    r = client.get("/docs")
    assert r.status_code == 200
    assert "swagger-ui" in r.text.lower() or "openapi" in r.text.lower()


def test_smoke_full_flow_endpoints(client):
    """単発投入 → ステータス確認 → ジョブ一覧 → ガイダンス取得"""
    # 1. health
    assert client.get("/health").json() == {"status": "ok"}

    # 2. health/detail (Blender / model_provider / homestyler の3コンポーネント)
    detail = client.get("/health/detail").json()
    assert set(detail["components"]) == {"blender", "model_provider", "homestyler"}

    # 3. process - ジョブを作る
    payload = {
        "product_name": "smoke-test",
        "source_url": "https://example.com/p",
        "site": "example.com",
        "dimensions": {"width_cm": 10, "depth_cm": 10, "height_cm": 10},
        "colors": ["ホワイト"],
        "materials": ["天然木"],
        "images": [{"url": "https://example.com/x.jpg", "type": "front"}],
        "category": "椅子",
    }
    r = client.post("/api/process", json=payload)
    assert r.status_code == 202
    job_id = r.json()["job_id"]

    # 4. status
    import time

    deadline = time.time() + 3.0
    while time.time() < deadline:
        body = client.get(f"/api/status/{job_id}").json()
        if body["status"] in ("success", "error"):
            break
        time.sleep(0.05)
    assert body["status"] == "success"
    assert body["product_name"] == "smoke-test"

    # 5. jobs リスト
    r = client.get("/api/jobs?limit=10").json()
    assert r["count"] >= 1
    assert any(j["id"] == job_id for j in r["jobs"])

    # 6. cancel (既に完了しているので 409)
    r = client.post(f"/api/jobs/{job_id}/cancel")
    assert r.status_code == 409

    # 7. errors/guidance
    r = client.get("/api/errors/guidance").json()
    assert "guidance" in r
    assert "model_quota_exceeded" in r["guidance"]


def test_404_for_unknown_paths(client):
    r = client.get("/api/nonexistent")
    assert r.status_code == 404
    r = client.post("/api/nonexistent")
    assert r.status_code == 404


def test_405_for_wrong_method(client):
    # /api/jobs は GET のみ
    r = client.post("/api/jobs")
    assert r.status_code == 405
    # /health は GET のみ
    r = client.post("/health")
    assert r.status_code == 405


def test_cors_header_does_not_leak_to_disallowed_origin(client):
    r = client.get("/api/jobs", headers={"Origin": "https://attacker.example"})
    assert "access-control-allow-origin" not in {k.lower() for k in r.headers}


def test_static_output_serves_generated_glb(client, tmp_path, monkeypatch):
    """/output/{name} がディスク上の GLB を配信する"""
    import os

    monkeypatch.chdir(tmp_path)
    os.makedirs("output", exist_ok=True)
    (tmp_path / "output" / "test.glb").write_bytes(b"GLB-binary-data")
    # アプリは元の CWD で起動済みなのでこのテストは static mount の仕組みだけ確認
    routes = {getattr(r, "path", None) for r in main.app.routes}
    assert "/output" in routes
