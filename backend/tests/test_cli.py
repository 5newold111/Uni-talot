"""
ec3d CLI のコマンド分岐・引数解析を検証。httpx 呼び出しは respx でモック。
"""

import json
import sys
from pathlib import Path

import httpx
import pytest
import respx

# CLI モジュールをインポート
SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import ec3d_cli  # noqa: E402


@pytest.fixture(autouse=True)
def fast_sleep(monkeypatch):
    monkeypatch.setattr(ec3d_cli.time, "sleep", lambda _: None)


@respx.mock
def test_submit_prints_job_id(tmp_path, capsys):
    payload = {
        "product_name": "p",
        "source_url": "https://example.com/p",
        "site": "x",
        "dimensions": {},
        "colors": [],
        "materials": [],
        "images": [{"url": "https://example.com/x.jpg", "type": "front"}],
    }
    f = tmp_path / "p.json"
    f.write_text(json.dumps(payload))
    respx.post("http://localhost:3000/api/process").mock(
        return_value=httpx.Response(202, json={"job_id": "abc123", "status": "queued"})
    )
    assert ec3d_cli.main(["submit", str(f)]) == 0
    out = capsys.readouterr().out.strip()
    assert out == "abc123"


@respx.mock
def test_submit_with_wait_polls_until_success(tmp_path, capsys):
    payload = {
        "product_name": "p",
        "source_url": "https://example.com/p",
        "site": "x",
        "dimensions": {},
        "colors": [],
        "materials": [],
        "images": [{"url": "https://example.com/x.jpg", "type": "front"}],
    }
    f = tmp_path / "p.json"
    f.write_text(json.dumps(payload))
    respx.post("http://localhost:3000/api/process").mock(
        return_value=httpx.Response(202, json={"job_id": "j1", "status": "queued"})
    )
    respx.get("http://localhost:3000/api/status/j1").mock(
        side_effect=[
            httpx.Response(
                200,
                json={
                    "id": "j1",
                    "status": "running",
                    "step": "generating_3d",
                    "step_index": 2,
                    "total_steps": 3,
                    "message": "[2/3] ...",
                    "result": None,
                    "error": None,
                    "error_code": None,
                    "cancel_requested": False,
                    "product_name": "p",
                    "created_at": 1.0,
                    "updated_at": 2.0,
                },
            ),
            httpx.Response(
                200,
                json={
                    "id": "j1",
                    "status": "success",
                    "step": "done",
                    "step_index": 3,
                    "total_steps": 3,
                    "message": "完了",
                    "result": {"product": "p", "glb": "out.glb"},
                    "error": None,
                    "error_code": None,
                    "cancel_requested": False,
                    "product_name": "p",
                    "created_at": 1.0,
                    "updated_at": 3.0,
                },
            ),
        ]
    )
    assert ec3d_cli.main(["submit", str(f), "--wait"]) == 0


@respx.mock
def test_status(capsys):
    respx.get("http://localhost:3000/api/status/xyz").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": "xyz",
                "status": "success",
                "step": "done",
                "step_index": 3,
                "total_steps": 3,
                "message": "ok",
                "result": {"glb": "a.glb"},
                "error": None,
                "error_code": None,
                "cancel_requested": False,
                "product_name": "p",
                "created_at": 1,
                "updated_at": 2,
            },
        )
    )
    assert ec3d_cli.main(["status", "xyz"]) == 0
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload["id"] == "xyz"


@respx.mock
def test_status_404_returns_nonzero(capsys):
    respx.get("http://localhost:3000/api/status/missing").mock(
        return_value=httpx.Response(404, json={"detail": "not found"})
    )
    assert ec3d_cli.main(["status", "missing"]) == 1


@respx.mock
def test_jobs_table_output(capsys):
    respx.get("http://localhost:3000/api/jobs?limit=20").mock(
        return_value=httpx.Response(
            200,
            json={
                "count": 2,
                "jobs": [
                    {
                        "id": "abc",
                        "status": "success",
                        "step": "done",
                        "product_name": "テーブル",
                        "step_index": 3,
                        "total_steps": 3,
                    },
                    {
                        "id": "def",
                        "status": "error",
                        "step": "generating_3d",
                        "product_name": "ソファ",
                        "step_index": 2,
                        "total_steps": 3,
                    },
                ],
            },
        )
    )
    assert ec3d_cli.main(["jobs"]) == 0
    out = capsys.readouterr().out
    assert "abc" in out and "def" in out
    assert "テーブル" in out and "ソファ" in out
    assert "JOB ID" in out  # ヘッダー


@respx.mock
def test_jobs_json_output(capsys):
    respx.get("http://localhost:3000/api/jobs?limit=20").mock(
        return_value=httpx.Response(200, json={"count": 0, "jobs": []})
    )
    assert ec3d_cli.main(["jobs", "--json"]) == 0
    body = json.loads(capsys.readouterr().out)
    assert body == {"count": 0, "jobs": []}


@respx.mock
def test_cancel_success():
    respx.post("http://localhost:3000/api/jobs/xyz/cancel").mock(
        return_value=httpx.Response(202, json={"cancel_requested": True, "job_id": "xyz"})
    )
    assert ec3d_cli.main(["cancel", "xyz"]) == 0


@respx.mock
def test_cancel_finished_returns_nonzero():
    respx.post("http://localhost:3000/api/jobs/done/cancel").mock(
        return_value=httpx.Response(409, json={"detail": "already done"})
    )
    assert ec3d_cli.main(["cancel", "done"]) == 1


@respx.mock
def test_upload_homestyler_command():
    respx.post("http://localhost:3000/api/jobs/j1/upload-to-homestyler").mock(
        return_value=httpx.Response(202, json={"job_id": "j1", "status": "queued_homestyler"})
    )
    assert ec3d_cli.main(["upload-homestyler", "j1"]) == 0


def test_api_key_header_is_sent(monkeypatch):
    monkeypatch.setattr(ec3d_cli, "API_KEY", "test-key")
    h = ec3d_cli._headers()
    assert h["X-API-Key"] == "test-key"


def test_no_api_key_header_when_unset(monkeypatch):
    monkeypatch.setattr(ec3d_cli, "API_KEY", "")
    h = ec3d_cli._headers()
    assert "X-API-Key" not in h
