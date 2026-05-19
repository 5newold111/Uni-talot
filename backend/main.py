import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.process import router as process_router
from services.cleanup import cleanup_output
from services.health_check import collect_health

load_dotenv()

os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("logs/app.log"), logging.StreamHandler()],
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    cleanup_output()
    yield


app = FastAPI(title="EC3D-Bridge API", lifespan=lifespan)

# Chrome 拡張機能 (chrome-extension://<ID>) と localhost からの呼び出しのみ許可。
# 任意オリジン公開はバックエンドへの不正リクエスト経路になるため、明示的に絞る。
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=(
        r"^(chrome-extension://[a-zA-Z0-9_-]+"
        r"|https?://localhost(:\d+)?"
        r"|https?://127\.0\.0\.1(:\d+)?)$"
    ),
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(process_router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/health/detail")
async def health_detail():
    return collect_health()
