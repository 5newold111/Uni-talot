"""
シンプルな X-API-Key 認証ミドルウェア。

`EC3D_API_KEY` 環境変数が設定されている場合のみ有効化される。
未設定なら認証スキップ (ローカル開発のデフォルト挙動)。
/health と /health/detail はヘルスチェック用に常に素通し。
"""

import os

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

# 認証不要なパス
PUBLIC_PATHS = frozenset({"/health", "/health/detail", "/docs", "/openapi.json", "/redoc"})
# 認証不要なプレフィックス (静的ファイル配信など)
PUBLIC_PREFIXES = ("/output/",)


class APIKeyMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, expected_key: str | None = None):
        super().__init__(app)
        self.expected_key = expected_key or os.getenv("EC3D_API_KEY", "")

    async def dispatch(self, request: Request, call_next):
        # 設定されていなければ素通し
        if not self.expected_key:
            return await call_next(request)
        # 公開エンドポイントは素通し
        if request.url.path in PUBLIC_PATHS:
            return await call_next(request)
        if any(request.url.path.startswith(p) for p in PUBLIC_PREFIXES):
            return await call_next(request)
        # CORS preflight は素通し (実リクエストでチェック)
        if request.method == "OPTIONS":
            return await call_next(request)
        provided = request.headers.get("x-api-key", "")
        if provided != self.expected_key:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or missing X-API-Key header"},
            )
        return await call_next(request)
