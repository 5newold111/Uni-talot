import time
import pytest
from services.job_manager import JobManager, STEPS, TOTAL_STEPS


async def test_create_returns_queued_job():
    mgr = JobManager()
    job = await mgr.create("テスト商品")
    assert job.status == "queued"
    assert job.step == "queued"
    assert job.step_index == 0
    assert job.total_steps == TOTAL_STEPS == 4
    assert job.product_name == "テスト商品"
    assert job.result is None
    assert job.error is None


async def test_get_returns_none_for_unknown_id():
    mgr = JobManager()
    assert await mgr.get("missing") is None


async def test_update_step_advances_index():
    mgr = JobManager()
    job = await mgr.create("p")
    for expected_idx, step in enumerate(STEPS):
        await mgr.update(job.id, step=step)
        current = await mgr.get(job.id)
        # queued=0, downloading_image=1, ..., done=5 だが step_index は TOTAL_STEPS でクランプ
        assert current.step == step
        assert current.step_index == min(expected_idx, TOTAL_STEPS)


async def test_update_records_result_and_error_separately():
    mgr = JobManager()
    job = await mgr.create("p")
    await mgr.update(job.id, status="success", result={"glb": "out.glb"})
    j = await mgr.get(job.id)
    assert j.status == "success"
    assert j.result == {"glb": "out.glb"}
    assert j.error is None

    await mgr.update(job.id, status="error", error="boom")
    j = await mgr.get(job.id)
    assert j.error == "boom"


async def test_update_unknown_id_is_noop():
    mgr = JobManager()
    # Should not raise
    await mgr.update("nope", status="success")


async def test_gc_drops_old_jobs():
    mgr = JobManager(retention_seconds=10)
    j1 = await mgr.create("a")
    # 古さを偽装（保持期間を超えている）
    j1.updated_at = time.time() - 1000
    # 新規作成時にGCが走り、j1 が削除される
    j2 = await mgr.create("b")
    assert await mgr.get(j1.id) is None
    assert await mgr.get(j2.id) is not None
