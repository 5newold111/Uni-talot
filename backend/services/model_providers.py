"""
3D 生成プロバイダー抽象。

設計: `MODEL_PROVIDER` 環境変数でプロバイダーを切り替える。

  - `tripo` (default): fal.ai Tripo 2.5 (有料、月数百〜数千円)
  - `colab_trellis`: Google Colab で立てた TRELLIS バックエンド (無料、要セットアップ)
  - `hf_space`: HuggingFace Space (将来対応予定)

各プロバイダーは ModelProvider プロトコル (`generate(image_path) -> bytes`) を実装する。
共通の SHA-256 キャッシュ機構 (`output/<hash>_raw.glb`) は generate_3d_model() で提供。

ADR-006 を参照。
"""

from __future__ import annotations

import base64
import logging
import os
from abc import ABC, abstractmethod

import httpx

from services.errors import ErrorCode, PipelineError
from services.http_retry import request_with_retry

logger = logging.getLogger(__name__)


class ModelProvider(ABC):
    """3D 生成プロバイダーのインタフェース。"""

    name: str = "abstract"

    @abstractmethod
    async def generate(self, image_path: str) -> bytes:
        """画像ファイルパスを受け取り、GLB バイナリを返す。失敗時は PipelineError を投げる。"""


# ---- 1. Tripo (fal.ai) ----------------------------------------------------


class TripoFalProvider(ModelProvider):
    """fal.ai 経由で Tripo 2.5 を呼ぶ (有料・既存実装)"""

    name = "tripo"
    ENDPOINT = "https://fal.run/fal-ai/tripo3d/v2.5/image-to-3d"

    def __init__(self, api_key: str):
        if not api_key or api_key == "your_fal_api_key_here":
            raise PipelineError(
                ErrorCode.MODEL_API_KEY_MISSING,
                "FAL_API_KEY が .env に設定されていません",
            )
        self.api_key = api_key

    async def generate(self, image_path: str) -> bytes:
        with open(image_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        data_uri = f"data:image/jpeg;base64,{b64}"

        headers = {
            "Authorization": f"Key {self.api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=180) as client:
            response = await request_with_retry(
                client,
                "POST",
                self.ENDPOINT,
                headers=headers,
                json={"image_url": data_uri, "texture_quality": "high", "output_format": "glb"},
            )

        if response.status_code != 200:
            code = (
                ErrorCode.MODEL_QUOTA_EXCEEDED
                if response.status_code in (402, 429)
                else ErrorCode.MODEL_GENERATION_FAILED
            )
            logger.warning(f"Tripo API error body: {response.text[:500]}")
            raise PipelineError(
                code, f"Tripo APIエラー: status={response.status_code} (詳細はログ参照)"
            )

        glb_url = (response.json().get("model_mesh") or {}).get("url", "")
        if not glb_url:
            raise PipelineError(
                ErrorCode.MODEL_GENERATION_FAILED, "Tripo APIから glb_url が取得できませんでした"
            )

        async with httpx.AsyncClient(timeout=60) as client:
            glb_resp = await request_with_retry(client, "GET", glb_url)
        if glb_resp.status_code != 200:
            raise PipelineError(
                ErrorCode.MODEL_GENERATION_FAILED,
                f"GLB ダウンロード失敗: {glb_resp.status_code}",
            )
        return glb_resp.content


# ---- 2. Colab TRELLIS (無料) ---------------------------------------------


class ColabTrellisProvider(ModelProvider):
    """Google Colab で立てた TRELLIS バックエンドを叩く (完全無料)

    Colab 側の API は docs/trellis_colab.ipynb に定義:
      POST <colab_url>/generate  (multipart/form-data: file)
      Response: image/gltf-binary (GLB バイナリ)
    """

    name = "colab_trellis"

    def __init__(self, base_url: str):
        if not base_url or base_url == "https://your-ngrok-url-here.ngrok-free.app":
            raise PipelineError(
                ErrorCode.MODEL_API_KEY_MISSING,
                "TRELLIS_COLAB_URL が未設定。docs/trellis_colab.ipynb を Colab で起動し、"
                "表示された ngrok URL を .env に設定してください",
            )
        self.base_url = base_url.rstrip("/")

    async def generate(self, image_path: str) -> bytes:
        url = f"{self.base_url}/generate"
        with open(image_path, "rb") as f:
            files = {"file": (os.path.basename(image_path), f.read(), "image/jpeg")}

        # Colab + ngrok のレイテンシは大きいので長めのタイムアウト
        async with httpx.AsyncClient(timeout=300) as client:
            response = await request_with_retry(client, "POST", url, files=files, max_attempts=2)

        if response.status_code != 200:
            # ngrok 切れ / Colab セッション切れの場合は明確にメッセージを出す
            if response.status_code in (404, 502, 503):
                raise PipelineError(
                    ErrorCode.MODEL_GENERATION_FAILED,
                    f"Colab バックエンド未到達 (status={response.status_code})。"
                    "Colab セッションが切れた可能性。docs/trellis_colab.ipynb を再起動して "
                    "新しい ngrok URL を .env に反映してください",
                )
            raise PipelineError(
                ErrorCode.MODEL_GENERATION_FAILED,
                f"Colab TRELLIS エラー: status={response.status_code}",
            )

        # Colab 側はバイナリ直接返却を約束している
        ctype = response.headers.get("content-type", "")
        if "gltf" not in ctype and "octet-stream" not in ctype:
            # 念のため body のサイズだけログに残す (中身は機微情報ではないがログ量抑制)
            logger.warning(f"想定外 Content-Type: {ctype}, body={len(response.content)}B")
        return response.content


# ---- 3. HuggingFace Space (gradio_client 経由 — 将来拡張) ----------------


class HuggingFaceSpaceProvider(ModelProvider):
    """HuggingFace の TRELLIS / Hunyuan3D Space を gradio_client 経由で叩く。
    現状はスタブ。実装するには gradio_client 依存追加と Space 個別の API 仕様調整が必要。"""

    name = "hf_space"

    async def generate(self, image_path: str) -> bytes:
        raise PipelineError(
            ErrorCode.MODEL_GENERATION_FAILED,
            "hf_space プロバイダーは未実装。'tripo' か 'colab_trellis' を使ってください",
        )


# ---- ファクトリー ---------------------------------------------------------


def get_provider() -> ModelProvider:
    """環境変数 MODEL_PROVIDER に基づきプロバイダーインスタンスを返す。"""
    name = os.getenv("MODEL_PROVIDER", "tripo").lower()
    if name == "tripo":
        return TripoFalProvider(api_key=os.getenv("FAL_API_KEY", ""))
    if name == "colab_trellis":
        return ColabTrellisProvider(base_url=os.getenv("TRELLIS_COLAB_URL", ""))
    if name == "hf_space":
        return HuggingFaceSpaceProvider()
    raise PipelineError(
        ErrorCode.INVALID_INPUT,
        f"未知の MODEL_PROVIDER: {name}。 'tripo' / 'colab_trellis' / 'hf_space' のいずれか",
    )
