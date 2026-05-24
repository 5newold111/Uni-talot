"""
3D モデル生成オーケストレーター。

v2.2: プロバイダー抽象化 (ADR-006)。
  - SHA-256 でキャッシュキー計算 → ヒットすれば API を呼ばずに既存 GLB を返す
  - キャッシュ無ければ MODEL_PROVIDER env で選んだプロバイダーに委譲

プロバイダーの実装は services.model_providers にあります:
  - tripo:        fal.ai Tripo 2.5 (有料)
  - colab_trellis: Google Colab で立てた TRELLIS バックエンド (無料)
  - hf_space:    HuggingFace Space (将来対応)
"""

import hashlib
import logging
import os

import aiofiles

from services.model_providers import get_provider

logger = logging.getLogger(__name__)


# 互換用: 既存テストが model_generator.FAL_KEY を monkeypatch しているため残す
FAL_KEY = os.getenv("FAL_API_KEY", "")


def _file_sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


async def generate_3d_model(image_path: str) -> str:
    """画像ファイルパスから 3D モデル (GLB) を生成して保存パスを返す。
    画像 SHA-256 をキャッシュキーとし、既にキャッシュがあればプロバイダーを呼ばずに返す。"""
    os.makedirs("output", exist_ok=True)

    image_hash = _file_sha256(image_path)
    save_path = f"output/{image_hash[:16]}_raw.glb"

    if os.path.exists(save_path) and os.path.getsize(save_path) > 0:
        logger.info(f"3D生成キャッシュヒット: {save_path} (プロバイダー呼び出しスキップ)")
        return save_path

    # プロバイダーは env 変数 MODEL_PROVIDER から決まる (default: tripo)
    provider = get_provider()
    logger.info(f"3D生成プロバイダー: {provider.name}")
    glb_bytes = await provider.generate(image_path)

    async with aiofiles.open(save_path, "wb") as f:
        await f.write(glb_bytes)

    logger.info(f"{provider.name} 生成完了: {save_path} ({len(glb_bytes)}B)")
    return save_path
