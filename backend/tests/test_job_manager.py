import sqlite3
import time

import pytest

from services.job_manager import STEPS, TOTAL_STEPS, JobManager


@pytest.fixture
def mgr(tmp_path):
    return JobManager(db_path=str(tmp_path / "jobs.db"))


async def test_create_returns_queued_job(mgr):
    job = await mgr.create("テスト商品")
    assert job.status == "queued"
    assert job.step == "queued"
    assert job.step_index == 0
    assert job.total_steps == TOTAL_STEPS == 3
    assert job.product_name == "テスト商品"
    assert job.result is None
    assert job.error is None


async def test_get_returns_none_for_unknown_id(mgr):
    assert await mgr.get("missing") is None


async def test_create_persists_across_manager_instances(tmp_path):
    db = str(tmp_path / "persist.db")
    mgr1 = JobManager(db_path=db)
    j = await mgr1.create("永続テスト")
    await mgr1.update(j.id, status="success", step="done", result={"glb": "x.glb"})

    # 新しいインスタンスで同じDBを開く
    mgr2 = JobManager(db_path=db)
    loaded = await mgr2.get(j.id)
    assert loaded is not None
    assert loaded.product_name == "永続テスト"
    assert loaded.status == "success"
    assert loaded.result == {"glb": "x.glb"}


async def test_update_step_advances_index(mgr):
    job = await mgr.create("p")
    for expected_idx, step in enumerate(STEPS):
        await mgr.update(job.id, step=step)
        current = await mgr.get(job.id)
        assert current.step == step
        assert current.step_index == min(expected_idx, TOTAL_STEPS)


async def test_update_records_result_and_error_separately(mgr):
    job = await mgr.create("p")
    await mgr.update(job.id, status="success", result={"glb": "out.glb"})
    j = await mgr.get(job.id)
    assert j.status == "success"
    assert j.result == {"glb": "out.glb"}
    assert j.error is None

    await mgr.update(job.id, status="error", error="boom")
    j = await mgr.get(job.id)
    assert j.error == "boom"


async def test_update_unknown_id_is_noop(mgr):
    # 例外を投げず、行も増えない
    await mgr.update("nope", status="success")
    assert await mgr.get("nope") is None


async def test_gc_drops_old_jobs(tmp_path):
    db = str(tmp_path / "gc.db")
    mgr = JobManager(db_path=db, retention_seconds=10)
    j1 = await mgr.create("a")
    # 直接SQLでupdated_atを古い値に書き換える
    with sqlite3.connect(db) as c:
        c.execute("UPDATE jobs SET updated_at = ? WHERE id = ?", (time.time() - 1000, j1.id))
    # 新規作成時にGCが走り、j1 が削除される
    j2 = await mgr.create("b")
    assert await mgr.get(j1.id) is None
    assert await mgr.get(j2.id) is not None


async def test_list_recent_orders_by_created_at_desc(mgr):
    a = await mgr.create("古い")
    # 明示的に created_at を進める
    await asyncio_sleep(0.01)
    b = await mgr.create("新しい")
    await asyncio_sleep(0.01)
    c = await mgr.create("最新")

    recent = await mgr.list_recent(limit=10)
    assert [j.id for j in recent] == [c.id, b.id, a.id]


async def test_list_recent_respects_limit(mgr):
    for i in range(5):
        await mgr.create(f"p{i}")
    recent = await mgr.list_recent(limit=2)
    assert len(recent) == 2


async def asyncio_sleep(seconds):
    import asyncio

    await asyncio.sleep(seconds)
