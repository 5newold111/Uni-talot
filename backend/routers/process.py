import asyncio
import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field, HttpUrl, field_validator

from services.errors import USER_GUIDANCE, ErrorCode, PipelineError
from services.homestyler_bot import upload_to_homestyler
from services.image_downloader import download_main_image
from services.job_manager import jobs
from services.model_generator import generate_3d_model
from services.scale_correction import apply_real_scale

router = APIRouter()
logger = logging.getLogger(__name__)


class ImageRef(BaseModel):
    url: HttpUrl
    type: str = Field(default="other", max_length=20)


class ProductData(BaseModel):
    product_name: str = Field(min_length=1, max_length=500)
    source_url: HttpUrl
    site: str = Field(min_length=1, max_length=200)
    dimensions: dict[str, float] = Field(default_factory=dict)
    colors: list[str] = Field(default_factory=list, max_length=20)
    materials: list[str] = Field(default_factory=list, max_length=20)
    images: list[ImageRef] = Field(min_length=1, max_length=50)
    category: str | None = Field(default="家具", max_length=50)

    @field_validator("dimensions")
    @classmethod
    def _validate_dimensions(cls, v: dict[str, float]) -> dict[str, float]:
        for key in ("width_cm", "depth_cm", "height_cm"):
            if key in v:
                val = v[key]
                if not isinstance(val, (int, float)):
                    raise ValueError(f"{key} は数値である必要があります")
                if val < 0 or val > 1000:
                    raise ValueError(
                        f"{key} は 0〜1000cm の範囲で指定してください (received {val})"
                    )
        return v


async def _run_pipeline(job_id: str, data: ProductData) -> None:
    logger.info(f"[{job_id}] 処理開始: {data.product_name}")
    try:
        await jobs.update(
            job_id,
            status="running",
            step="downloading_image",
            message="[1/4] 商品画像をダウンロードしています...",
        )
        # ImageRef を従来のサービスが期待する dict 形式に変換
        images = [img.model_dump(mode="json") for img in data.images]
        image_path = await download_main_image(images)

        await jobs.update(
            job_id, step="generating_3d", message="[2/4] 3Dモデルを生成しています（30秒〜2分）..."
        )
        raw_glb_path = await generate_3d_model(image_path)

        w = data.dimensions.get("width_cm", 0)
        d = data.dimensions.get("depth_cm", 0)
        h = data.dimensions.get("height_cm", 0)
        await jobs.update(
            job_id, step="scaling", message=f"[3/4] 実寸（W{w}×D{d}×H{h}cm）にスケール補正中..."
        )
        scaled_glb_path = await asyncio.to_thread(apply_real_scale, raw_glb_path, w, d, h)

        await jobs.update(
            job_id,
            step="uploading_homestyler",
            message="[4/4] Homestylerにアップロード中...",
        )
        await upload_to_homestyler(
            glb_path=scaled_glb_path,
            product_name=data.product_name,
            dimensions=data.dimensions,
            category=data.category or "家具",
        )

        await jobs.update(
            job_id,
            status="success",
            step="done",
            message=f"完了: {data.product_name} を Homestyler に登録しました",
            result={"product": data.product_name, "glb": scaled_glb_path},
        )
        logger.info(f"[{job_id}] 完了: {data.product_name}")

    except PipelineError as e:
        logger.error(f"[{job_id}] {e}")
        guidance = USER_GUIDANCE.get(e.code, "")
        await jobs.update(
            job_id,
            status="error",
            message=f"エラー: {e.message}" + (f" / {guidance}" if guidance else ""),
            error=e.message,
            error_code=e.code.value,
        )
    except Exception as e:
        logger.exception(f"[{job_id}] 予期しないエラー: {e}")
        await jobs.update(
            job_id,
            status="error",
            message=f"内部エラー: {str(e)}",
            error=str(e),
            error_code=ErrorCode.INTERNAL_ERROR.value,
        )


@router.post("/process", status_code=202)
async def process_product(data: ProductData, background_tasks: BackgroundTasks):
    job = await jobs.create(data.product_name)
    background_tasks.add_task(_run_pipeline, job.id, data)
    return {"job_id": job.id, "status": job.status}


@router.get("/status/{job_id}")
async def get_status(job_id: str):
    job = await jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job_id が見つかりません")
    return job.to_dict()


@router.get("/jobs")
async def list_jobs(limit: int = 50):
    if limit < 1 or limit > 500:
        raise HTTPException(status_code=400, detail="limit は 1〜500 で指定してください")
    recent = await jobs.list_recent(limit=limit)
    return {"jobs": [j.to_dict() for j in recent], "count": len(recent)}


@router.get("/errors/guidance")
async def error_guidance():
    """フロントエンドが error_code → ユーザー向けメッセージを引くための辞書を返す。"""
    return {"guidance": {k.value: v for k, v in USER_GUIDANCE.items()}}
