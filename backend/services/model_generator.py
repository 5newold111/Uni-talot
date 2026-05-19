"""
3Dモデル生成: fal.ai Tripo 2.5 API を使って画像から GLB を生成する。

Phase 1 で TRELLIS 2 / HuggingFace を併用する設計だったが、
TRELLIS 2 は HuggingFace Inference API では提供されていない (Gradio Space のみ) ため
Tripo (fal.ai) ルートに一本化した。HF Inference を再導入する場合は
https://huggingface.co/microsoft/TRELLIS の最新情報を確認すること。
"""

import base64
import hashlib
import logging
import os

import aiofiles
import httpx
from dotenv import load_dotenv

from services.http_retry import request_with_retry

load_dotenv()
logger = logging.getLogger(__name__)

FAL_KEY = os.getenv("FAL_API_KEY", "")


def _file_sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


async def generate_3d_model(image_path: str) -> str:
    """画像ファイルパスから3Dモデル (GLB) を生成して保存パスを返す。
    画像 SHA-256 をキャッシュキーとし、既にキャッシュがあれば API を呼ばずに返す。"""
    os.makedirs("output", exist_ok=True)

    if not FAL_KEY or FAL_KEY == "your_fal_api_key_here":
        raise RuntimeError("FAL_API_KEY が .env に設定されていません")

    image_hash = _file_sha256(image_path)
    save_path = f"output/{image_hash[:16]}_raw.glb"

    if os.path.exists(save_path) and os.path.getsize(save_path) > 0:
        logger.info(f"3D生成キャッシュヒット: {save_path} (skipping Tripo API call)")
        return save_path

    with open(image_path, "rb") as f:
        image_b64 = base64.b64encode(f.read()).decode()
    image_data_uri = f"data:image/jpeg;base64,{image_b64}"

    headers = {
        "Authorization": f"Key {FAL_KEY}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=180) as client:
        response = await request_with_retry(
            client,
            "POST",
            "https://fal.run/fal-ai/tripo3d/v2.5/image-to-3d",
            headers=headers,
            json={
                "image_url": image_data_uri,
                "texture_quality": "high",
                "output_format": "glb",
            },
        )

    if response.status_code != 200:
        raise RuntimeError(f"Tripo APIエラー: {response.status_code} {response.text[:300]}")

    result = response.json()
    glb_url = (result.get("model_mesh") or {}).get("url", "")
    if not glb_url:
        raise RuntimeError(f"Tripo APIから glb_url が取得できませんでした: {result}")

    async with httpx.AsyncClient(timeout=60) as client:
        glb_response = await request_with_retry(client, "GET", glb_url)
    if glb_response.status_code != 200:
        raise RuntimeError(f"GLB ダウンロード失敗: {glb_response.status_code}")

    async with aiofiles.open(save_path, "wb") as f:
        await f.write(glb_response.content)

    logger.info(f"Tripo 生成完了: {save_path}")
    return save_path
