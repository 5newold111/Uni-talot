"""
SQLite ベースの Job ストア。サーバー再起動でジョブが失われない。

DB パスは環境変数 JOB_DB_PATH で指定 (default: jobs.db, 相対パス)。
テストでは tmp_path / "test.db" を渡すか、conftest.py で JOB_DB_PATH を
一時ファイルに切り替える。
"""

import asyncio
import json
import os
import sqlite3
import time
import uuid
from dataclasses import asdict, dataclass, field

STEPS = [
    "queued",
    "downloading_image",
    "generating_3d",
    "scaling",
    "uploading_homestyler",
    "done",
]
TOTAL_STEPS = len(STEPS) - 2  # queued/done を除いた 4 ステップ


@dataclass
class Job:
    id: str
    product_name: str
    status: str = "queued"
    step: str = "queued"
    step_index: int = 0
    total_steps: int = TOTAL_STEPS
    message: str = "キュー登録済み"
    result: dict | None = None
    error: str | None = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return asdict(self)


SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    product_name TEXT NOT NULL,
    status TEXT NOT NULL,
    step TEXT NOT NULL,
    step_index INTEGER NOT NULL,
    total_steps INTEGER NOT NULL,
    message TEXT NOT NULL,
    result TEXT,
    error TEXT,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_jobs_updated_at ON jobs(updated_at);
CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at);
"""


def _row_to_job(row: sqlite3.Row) -> Job:
    d = dict(row)
    d["result"] = json.loads(d["result"]) if d["result"] else None
    return Job(**d)


class JobManager:
    def __init__(self, db_path: str = "jobs.db", retention_seconds: int = 7 * 24 * 3600):
        self._db_path = db_path
        self._retention = retention_seconds
        # 親ディレクトリは事前に存在している前提（テストは tmp_path 直下に作る）
        if db_path != ":memory:":
            parent = os.path.dirname(os.path.abspath(db_path))
            if parent:
                os.makedirs(parent, exist_ok=True)
        with self._conn() as c:
            c.executescript(SCHEMA)

    def _conn(self) -> sqlite3.Connection:
        c = sqlite3.connect(self._db_path)
        c.row_factory = sqlite3.Row
        return c

    async def create(self, product_name: str) -> Job:
        return await asyncio.to_thread(self._create_sync, product_name)

    def _create_sync(self, product_name: str) -> Job:
        job = Job(id=uuid.uuid4().hex[:12], product_name=product_name)
        with self._conn() as c:
            c.execute(
                """INSERT INTO jobs
                   (id, product_name, status, step, step_index, total_steps,
                    message, result, error, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    job.id,
                    job.product_name,
                    job.status,
                    job.step,
                    job.step_index,
                    job.total_steps,
                    job.message,
                    None,
                    None,
                    job.created_at,
                    job.updated_at,
                ),
            )
        self._gc_sync()
        return job

    async def get(self, job_id: str) -> Job | None:
        return await asyncio.to_thread(self._get_sync, job_id)

    def _get_sync(self, job_id: str) -> Job | None:
        with self._conn() as c:
            row = c.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return _row_to_job(row) if row else None

    async def list_recent(self, limit: int = 50) -> list[Job]:
        return await asyncio.to_thread(self._list_recent_sync, limit)

    def _list_recent_sync(self, limit: int) -> list[Job]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [_row_to_job(r) for r in rows]

    async def update(
        self,
        job_id: str,
        *,
        status: str | None = None,
        step: str | None = None,
        message: str | None = None,
        result: dict | None = None,
        error: str | None = None,
    ) -> None:
        await asyncio.to_thread(self._update_sync, job_id, status, step, message, result, error)

    def _update_sync(self, job_id, status, step, message, result, error) -> None:
        updates: dict = {"updated_at": time.time()}
        if status is not None:
            updates["status"] = status
        if step is not None:
            updates["step"] = step
            if step in STEPS:
                updates["step_index"] = max(0, min(TOTAL_STEPS, STEPS.index(step)))
        if message is not None:
            updates["message"] = message
        if result is not None:
            updates["result"] = json.dumps(result)
        if error is not None:
            updates["error"] = error
        set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
        with self._conn() as c:
            c.execute(
                f"UPDATE jobs SET {set_clause} WHERE id = ?",
                (*updates.values(), job_id),
            )

    def _gc_sync(self) -> int:
        cutoff = time.time() - self._retention
        with self._conn() as c:
            cur = c.execute("DELETE FROM jobs WHERE updated_at < ?", (cutoff,))
            return cur.rowcount


# モジュールロード時に作るグローバル。テストは conftest.py で JOB_DB_PATH を上書きする。
_DB_PATH = os.environ.get("JOB_DB_PATH", "jobs.db")
jobs = JobManager(db_path=_DB_PATH)
