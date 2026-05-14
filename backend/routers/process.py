import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from services.image_downloader import download_main_image
from services.model_generator import generate_3d_model
from services.scale_correction import apply_real_scale
from services.homestyler_bot import upload_to_homestyler

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


@router.post("/process")
async def process_product(data: ProductData):
    logger.info(f"処理開始: {data.product_name}")

    try:
        logger.info("[1/5] 商品画像をダウンロードしています...")
        image_path = await download_main_image(data.images)

        logger.info("[2/5] 3Dモデルを生成しています（30秒〜2分かかります）...")
        raw_glb_path = await generate_3d_model(image_path)

        w = data.dimensions.get("width_cm", 0)
        d = data.dimensions.get("depth_cm", 0)
        h = data.dimensions.get("height_cm", 0)
        logger.info(f"[3/5] 実寸（W{w}cm × D{d}cm × H{h}cm）にスケール補正しています...")
        scaled_glb_path = apply_real_scale(raw_glb_path, w, d, h)

        logger.info("[4/5] Homestylerにアップロードしています...")
        await upload_to_homestyler(
            glb_path=scaled_glb_path,
            product_name=data.product_name,
            dimensions=data.dimensions,
            category=data.category
        )

        logger.info(f"完了: {data.product_name} を Homestyler に登録しました")
        return {"status": "success", "product": data.product_name, "glb": scaled_glb_path}

    except Exception as e:
        logger.error(f"エラー発生: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
