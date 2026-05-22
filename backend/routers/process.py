import asyncio
import logging

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException
from pydantic import BaseModel, Field, HttpUrl, field_validator

from services.errors import USER_GUIDANCE, ErrorCode, PipelineError, guidance_for
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


async def _check_cancelled(job_id: str) -> bool:
    job = await jobs.get(job_id)
    return bool(job and job.cancel_requested)


async def _abort_if_cancelled(job_id: str) -> bool:
    if await _check_cancelled(job_id):
        await jobs.update(
            job_id,
            status="cancelled",
            message="ジョブはユーザーによってキャンセルされました",
        )
        logger.info(f"[{job_id}] cancelled by user request")
        return True
    return False


async def _run_pipeline(job_id: str, data: ProductData) -> None:
    """
    コアパイプライン: 画像DL → 3D生成 → スケール補正 (3ステップ)。

    Homestyler アップロードは v2.0 で分離済み。`POST /api/jobs/{id}/upload-to-homestyler`
    を別途呼ぶことで明示的に発火する。これにより:
      - Homestyler セレクター不一致でジョブ全体が失敗しなくなる
      - Tripo クレジットを消費して生成した GLB が確実に手元に残る
      - GLB を直接ダウンロード/プレビュー用途にも使える
    """
    log_extra = {"job_id": job_id}
    logger.info(f"[{job_id}] 処理開始: {data.product_name}", extra=log_extra)
    try:
        if await _abort_if_cancelled(job_id):
            return
        await jobs.update(
            job_id,
            status="running",
            step="downloading_image",
            message="[1/3] 商品画像をダウンロードしています...",
        )
        images = [img.model_dump(mode="json") for img in data.images]
        image_path = await download_main_image(images)

        if await _abort_if_cancelled(job_id):
            return
        await jobs.update(
            job_id, step="generating_3d", message="[2/3] 3Dモデルを生成しています（30秒〜2分）..."
        )
        raw_glb_path = await generate_3d_model(image_path)

        if await _abort_if_cancelled(job_id):
            return
        w = data.dimensions.get("width_cm", 0)
        d = data.dimensions.get("depth_cm", 0)
        h = data.dimensions.get("height_cm", 0)
        await jobs.update(
            job_id, step="scaling", message=f"[3/3] 実寸（W{w}×D{d}×H{h}cm）にスケール補正中..."
        )
        scaled_glb_path = await asyncio.to_thread(apply_real_scale, raw_glb_path, w, d, h)

        await jobs.update(
            job_id,
            status="success",
            step="done",
            message=f"完了: GLB を生成しました ({data.product_name})",
            # result には Homestyler 連携で必要な情報を全て格納しておく
            result={
                "product": data.product_name,
                "glb": scaled_glb_path,
                "dimensions": data.dimensions,
                "category": data.category or "家具",
                "source_url": str(data.source_url),
            },
        )
        logger.info(f"[{job_id}] 完了: {data.product_name}")

    except PipelineError as e:
        logger.error(
            f"[{job_id}] {e}",
            extra={"job_id": job_id, "error_code": e.code.value},
        )
        guidance = USER_GUIDANCE.get(e.code, "")
        await jobs.update(
            job_id,
            status="error",
            message=f"エラー: {e.message}" + (f" / {guidance}" if guidance else ""),
            error=e.message,
            error_code=e.code.value,
        )
    except Exception as e:
        logger.exception(
            f"[{job_id}] 予期しないエラー: {e}",
            extra={"job_id": job_id, "error_code": ErrorCode.INTERNAL_ERROR.value},
        )
        await jobs.update(
            job_id,
            status="error",
            message=f"内部エラー: {str(e)}",
            error=str(e),
            error_code=ErrorCode.INTERNAL_ERROR.value,
        )


async def _run_homestyler_upload(job_id: str) -> None:
    """別ジョブとして Homestyler アップロードを実行する。失敗してもコアジョブには影響しない。"""
    job = await jobs.get(job_id)
    if not job or not job.result:
        return
    log_extra = {"job_id": job_id}
    try:
        await jobs.update(
            job_id,
            status="running",
            step="uploading_homestyler",
            message="Homestyler にアップロード中...",
        )
        await upload_to_homestyler(
            glb_path=job.result["glb"],
            product_name=job.result["product"],
            dimensions=job.result.get("dimensions", {}),
            category=job.result.get("category", "家具"),
        )
        await jobs.update(
            job_id,
            status="success",
            step="done",
            message=f"完了: {job.result['product']} を Homestyler に登録しました",
        )
        logger.info(f"[{job_id}] Homestyler 登録完了", extra=log_extra)
    except PipelineError as e:
        logger.error(
            f"[{job_id}] Homestyler 失敗 {e}", extra={**log_extra, "error_code": e.code.value}
        )
        await jobs.update(
            job_id,
            status="error",
            error=e.message,
            error_code=e.code.value,
            message=f"Homestyler エラー: {e.message}",
        )
    except Exception as e:
        logger.exception(f"[{job_id}] Homestyler 予期しないエラー", extra=log_extra)
        await jobs.update(
            job_id,
            status="error",
            error=str(e),
            error_code=ErrorCode.UPLOAD_FAILED.value,
            message=f"Homestyler エラー: {e}",
        )


@router.post("/process", status_code=202)
async def process_product(data: ProductData, background_tasks: BackgroundTasks):
    """3D 生成パイプラインを起動する (Homestyler アップロードは含まない)。"""
    job = await jobs.create(data.product_name)
    background_tasks.add_task(_run_pipeline, job.id, data)
    return {"job_id": job.id, "status": job.status}


@router.post("/jobs/{job_id}/upload-to-homestyler", status_code=202)
async def trigger_homestyler_upload(job_id: str, background_tasks: BackgroundTasks):
    """成功済みジョブの GLB を Homestyler にアップロードする (オプショナル後処理)。

    パイプラインから切り離されているので、Homestyler が失敗してもコアジョブの
    'success' 状態は元の result に保存されている。ジョブのステータスは新たに
    'running' → 'success'/'error' に変わる。"""
    job = await jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job_id が見つかりません")
    if not job.result or "glb" not in job.result:
        raise HTTPException(
            status_code=409,
            detail=f"GLB が存在しません (status={job.status})。先に /api/process を成功させてください",
        )
    background_tasks.add_task(_run_homestyler_upload, job_id)
    return {"job_id": job_id, "status": "queued_homestyler"}


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


@router.post("/jobs/{job_id}/cancel", status_code=202)
async def cancel_job(job_id: str):
    """ジョブにキャンセルフラグを立てる。実行中の場合は次のステップ境界で中断する。"""
    job = await jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job_id が見つかりません")
    if job.status in ("success", "error", "cancelled"):
        raise HTTPException(status_code=409, detail=f"ジョブは既に終端状態です: {job.status}")
    ok = await jobs.request_cancel(job_id)
    return {"cancel_requested": ok, "job_id": job_id}


@router.get("/errors/guidance")
async def error_guidance(accept_language: str = Header(default="ja")):
    """フロントエンドが error_code → ユーザー向けメッセージを引くための辞書を返す。
    Accept-Language ヘッダの先頭値が "en*" なら英語、それ以外は日本語。"""
    primary = accept_language.split(",")[0].strip() if accept_language else "ja"
    table = guidance_for(primary)
    return {
        "language": "en" if primary.lower().startswith("en") else "ja",
        "guidance": {k.value: v for k, v in table.items()},
    }


# 後方互換: ガイダンス辞書のデフォルト (日本語) も保持
_ = USER_GUIDANCE
