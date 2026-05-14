import os
import httpx
import aiofiles
import uuid
import logging
import base64
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

HF_TOKEN = os.getenv("HF_TOKEN", "")
FAL_KEY = os.getenv("FAL_API_KEY", "")
USE_TRIPO = os.getenv("USE_TRIPO", "false").lower() == "true"


async def generate_3d_model(image_path: str) -> str:
    """
    画像ファイルパスから3Dモデル（GLB）を生成して保存パスを返す。
    USE_TRIPO=true の場合は Tripo API、false の場合は TRELLIS 2 を使用。
    """
    os.makedirs("output", exist_ok=True)

    if USE_TRIPO:
        logger.info("→ Tripo API (fal.ai) を使用して生成します")
        return await _generate_with_tripo(image_path)
    else:
        logger.info("→ TRELLIS 2 (HuggingFace) を使用して生成します")
        return await _generate_with_trellis(image_path)


async def _generate_with_trellis(image_path: str) -> str:
    """TRELLIS 2 (HuggingFace Inference API) で GLB を生成する"""
    if not HF_TOKEN:
        raise RuntimeError("HF_TOKEN が .env に設定されていません")

    with open(image_path, "rb") as f:
        image_b64 = base64.b64encode(f.read()).decode()

    headers = {
        "Authorization": f"Bearer {HF_TOKEN}",
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient(timeout=300) as client:
        response = await client.post(
            "https://api-inference.huggingface.co/models/microsoft/TRELLIS-image-large",
            headers=headers,
            json={"inputs": image_b64, "options": {"wait_for_model": True}}
        )

    if response.status_code != 200:
        raise RuntimeError(f"TRELLIS 2 APIエラー: {response.status_code} {response.text[:300]}")

    content_type = response.headers.get("content-type", "")
    if "application/json" in content_type:
        result = response.json()
        glb_url = result.get("glb_url") or (result[0].get("url", "") if isinstance(result, list) else "")
        if not glb_url:
            raise RuntimeError(f"TRELLIS 2 APIから glb_url が取得できませんでした: {result}")
        async with httpx.AsyncClient(timeout=60) as client:
            glb_response = await client.get(glb_url)
        glb_bytes = glb_response.content
    else:
        glb_bytes = response.content

    save_path = f"output/{uuid.uuid4()}_raw.glb"
    async with aiofiles.open(save_path, "wb") as f:
        await f.write(glb_bytes)

    logger.info(f"TRELLIS 2 生成完了: {save_path}")
    return save_path


async def _generate_with_tripo(image_path: str) -> str:
    """Tripo v2.5 API (fal.ai 経由) で GLB を生成する"""
    if not FAL_KEY:
        raise RuntimeError("FAL_API_KEY が .env に設定されていません")

    with open(image_path, "rb") as f:
        image_b64 = base64.b64encode(f.read()).decode()
    image_data_uri = f"data:image/jpeg;base64,{image_b64}"

    headers = {
        "Authorization": f"Key {FAL_KEY}",
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient(timeout=180) as client:
        response = await client.post(
            "https://fal.run/fal-ai/tripo3d/v2.5/image-to-3d",
            headers=headers,
            json={
                "image_url": image_data_uri,
                "texture_quality": "high",
                "output_format": "glb"
            }
        )

    if response.status_code != 200:
        raise RuntimeError(f"Tripo APIエラー: {response.status_code} {response.text[:300]}")

    result = response.json()

    glb_url = result.get("model_mesh", {}).get("url", "")
    if not glb_url:
        raise RuntimeError(f"Tripo APIから glb_url が取得できませんでした: {result}")

    async with httpx.AsyncClient(timeout=60) as client:
        glb_response = await client.get(glb_url)

    save_path = f"output/{uuid.uuid4()}_raw.glb"
    async with aiofiles.open(save_path, "wb") as f:
        await f.write(glb_response.content)

    logger.info(f"Tripo 生成完了: {save_path}")
    return save_path
