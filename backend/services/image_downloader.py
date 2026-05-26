import logging
import os
import uuid
from io import BytesIO

import httpx
from PIL import Image

from services.errors import ErrorCode, PipelineError
from services.http_retry import request_with_retry
from services.url_safety import is_url_safe

logger = logging.getLogger(__name__)


async def download_main_image(images: list[dict]) -> str:
    """
    商品画像リストから最初の有効な画像をダウンロードして保存する。
    type="front" があればそれを優先する。

    SSRF 防御: URL は事前に is_url_safe() で内部 IP/予約 IP に解決されないことを検証する。
    """
    os.makedirs("output", exist_ok=True)

    sorted_images = sorted(
        images, key=lambda x: {"front": 0, "": 1, "side": 2}.get(x.get("type", ""), 1)
    )

    for img in sorted_images:
        url = img.get("url", "")
        if not url or not url.startswith("http"):
            continue
        # SSRF チェック
        safe, reason = is_url_safe(url)
        if not safe:
            logger.warning(f"安全でない URL をスキップ: {url} ({reason})")
            continue
        try:
            async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                response = await request_with_retry(
                    client,
                    "GET",
                    url,
                    headers={"User-Agent": "Mozilla/5.0 (compatible; EC3DBridge/1.0)"},
                )
            if response.status_code != 200:
                continue

            image = Image.open(BytesIO(response.content)).convert("RGB")
            if image.width < 400 or image.height < 400:
                logger.warning(
                    f"画像が小さすぎるためスキップ: {url} ({image.width}x{image.height})"
                )
                continue

            save_path = f"output/{uuid.uuid4()}_input.jpg"
            image.save(save_path, "JPEG", quality=95)
            logger.info(f"画像保存完了: {save_path} ({image.width}x{image.height})")
            return save_path

        except Exception as e:
            logger.warning(f"画像ダウンロード失敗 ({url}): {e}")
            continue

    raise PipelineError(
        ErrorCode.IMAGE_DOWNLOAD_FAILED,
        "有効な商品画像が1枚もダウンロードできませんでした",
    )
