import asyncio
import logging
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import Optional
from services.image_downloader import download_main_image
from services.model_generator import generate_3d_model
from services.scale_correction import apply_real_scale
from services.homestyler_bot import upload_to_homestyler
from services.job_manager import jobs

router = APIRouter()
logger = logging.getLogger(__name__)


class ProductData(BaseModel):
    product_name: str
    source_url: str
    site: str
    dimensions: dict
    colors: list[str]
    materials: list[str]
    images: list[dict]
    category: Optional[str] = "家具"


async def _run_pipeline(job_id: str, data: ProductData) -> None:
    logger.info(f"[{job_id}] 処理開始: {data.product_name}")
    try:
        await jobs.update(job_id, status="running",
                          step="downloading_image",
                          message="[1/4] 商品画像をダウンロードしています...")
        image_path = await download_main_image(data.images)

        await jobs.update(job_id, step="generating_3d",
                          message="[2/4] 3Dモデルを生成しています（30秒〜2分）...")
        raw_glb_path = await generate_3d_model(image_path)

        w = data.dimensions.get("width_cm", 0)
        d = data.dimensions.get("depth_cm", 0)
        h = data.dimensions.get("height_cm", 0)
        await jobs.update(job_id, step="scaling",
                          message=f"[3/4] 実寸（W{w}×D{d}×H{h}cm）にスケール補正中...")
        scaled_glb_path = await asyncio.to_thread(
            apply_real_scale, raw_glb_path, w, d, h
        )

        await jobs.update(job_id, step="uploading_homestyler",
                          message="[4/4] Homestylerにアップロード中...")
        await upload_to_homestyler(
            glb_path=scaled_glb_path,
            product_name=data.product_name,
            dimensions=data.dimensions,
            category=data.category,
        )

        await jobs.update(
            job_id,
            status="success", step="done",
            message=f"完了: {data.product_name} を Homestyler に登録しました",
            result={"product": data.product_name, "glb": scaled_glb_path},
        )
        logger.info(f"[{job_id}] 完了: {data.product_name}")

    except Exception as e:
        logger.exception(f"[{job_id}] エラー発生: {e}")
        await jobs.update(
            job_id,
            status="error",
            message=f"エラー: {str(e)}",
            error=str(e),
        )


@router.post("/process", status_code=202)
async def process_product(data: ProductData, background_tasks: BackgroundTasks):
    if not data.images:
        raise HTTPException(status_code=400, detail="images が空です")
    job = await jobs.create(data.product_name)
    background_tasks.add_task(_run_pipeline, job.id, data)
    return {"job_id": job.id, "status": job.status}


@router.get("/status/{job_id}")
async def get_status(job_id: str):
    job = await jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job_id が見つかりません")
    return job.to_dict()
