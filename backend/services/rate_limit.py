"""
シンプルなトークンバケットによるレートリミット。

`/api/process` は外部 API (fal.ai) と Playwright Chromium 起動を伴う重い処理なので、
誤操作や悪意のあるリクエストで予算枯渇しないよう、IP ベースでバケットを管理する。
"""

import time

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


class TokenBucket:
    """ノンロックの軽量トークンバケット (single-process 想定)"""

    def __init__(self, capacity: int = 10, refill_per_sec: float = 0.5):
        self.capacity = capacity
        self.refill_rate = refill_per_sec
        self._buckets: dict[str, tuple[float, float]] = {}

    def consume(self, key: str, n: int = 1) -> bool:
        now = time.monotonic()
        tokens, last = self._buckets.get(key, (float(self.capacity), now))
        # 経過時間に応じてリフィル
        elapsed = now - last
        tokens = min(float(self.capacity), tokens + elapsed * self.refill_rate)
        if tokens < n:
            self._buckets[key] = (tokens, now)
            return False
        self._buckets[key] = (tokens - n, now)
        return True


# レートリミット対象パスのプレフィックス
LIMITED_PREFIXES = ("/api/process",)


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        capacity: int = 10,
        refill_per_sec: float = 0.5,
    ):
        super().__init__(app)
        self.bucket = TokenBucket(capacity=capacity, refill_per_sec=refill_per_sec)

    async def dispatch(self, request: Request, call_next):
        if request.method != "POST":
            return await call_next(request)
        if not any(request.url.path.startswith(p) for p in LIMITED_PREFIXES):
            return await call_next(request)

        # IP は X-Forwarded-For があればそれを優先 (リバプロ越し対応)
        forwarded = request.headers.get("x-forwarded-for", "")
        key = (
            forwarded.split(",")[0].strip()
            if forwarded
            else (request.client.host if request.client else "unknown")
        )
        if not self.bucket.consume(key):
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please retry shortly."},
                headers={"Retry-After": "2"},
            )
        return await call_next(request)
