"""
シンプルなインメモリ Job Manager。
リスタートで失われるが、シングルプロセスFastAPIには十分。
"""
import asyncio
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Optional, Any

# 5ステップ定義
STEPS = [
    "queued",
    "downloading_image",
    "generating_3d",
    "scaling",
    "uploading_homestyler",
    "done",
]

TOTAL_STEPS = len(STEPS) - 2  # queued / done を除いた 4 ステップ


@dataclass
class Job:
    id: str
    product_name: str
    status: str = "queued"          # "queued" | "running" | "success" | "error"
    step: str = "queued"            # STEPS のいずれか
    step_index: int = 0             # 0..TOTAL_STEPS
    total_steps: int = TOTAL_STEPS
    message: str = "キュー登録済み"
    result: Optional[dict] = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return asdict(self)


class JobManager:
    def __init__(self, retention_seconds: int = 3600):
        self._jobs: dict[str, Job] = {}
        self._lock = asyncio.Lock()
        self._retention = retention_seconds

    async def create(self, product_name: str) -> Job:
        async with self._lock:
            job_id = uuid.uuid4().hex[:12]
            job = Job(id=job_id, product_name=product_name)
            self._jobs[job_id] = job
            self._gc_locked()
            return job

    async def get(self, job_id: str) -> Optional[Job]:
        async with self._lock:
            return self._jobs.get(job_id)

    async def update(
        self,
        job_id: str,
        *,
        status: Optional[str] = None,
        step: Optional[str] = None,
        message: Optional[str] = None,
        result: Optional[dict] = None,
        error: Optional[str] = None,
    ) -> None:
        async with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            if status is not None:
                job.status = status
            if step is not None:
                job.step = step
                if step in STEPS:
                    idx = STEPS.index(step)
                    job.step_index = max(0, min(TOTAL_STEPS, idx))
            if message is not None:
                job.message = message
            if result is not None:
                job.result = result
            if error is not None:
                job.error = error
            job.updated_at = time.time()

    def _gc_locked(self) -> None:
        cutoff = time.time() - self._retention
        stale = [jid for jid, j in self._jobs.items() if j.updated_at < cutoff]
        for jid in stale:
            self._jobs.pop(jid, None)


jobs = JobManager()
