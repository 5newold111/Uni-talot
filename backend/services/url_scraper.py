"""
サーバーサイドで EC 商品ページの HTML を取って簡易スクレイピング。

Chrome 拡張機能なしで使えるよう、og:image / og:title / 個別セレクタを
正規表現で抽出する最小実装。JS レンダリング必須の SPA は扱えない。

Chrome 拡張機能版の `extension/scrapers/site_configs.js` と機能的に
重複するが、運用上は使い分けを明示する:
  - 拡張機能: ブラウザ DOM 直接読み込み (正確、全 EC サイト対応)
  - サーバー側: og タグからの最小抽出 (拡張無しで使える、品質は控えめ)
"""

import logging
import re
from urllib.parse import urlparse

import httpx

from services.errors import ErrorCode, PipelineError
from services.url_safety import is_url_safe

logger = logging.getLogger(__name__)

OG_IMAGE_RE = re.compile(
    r'<meta\s+(?:property|name)\s*=\s*["\']og:image["\']\s+content\s*=\s*["\']([^"\']+)["\']',
    re.IGNORECASE,
)
OG_TITLE_RE = re.compile(
    r'<meta\s+(?:property|name)\s*=\s*["\']og:title["\']\s+content\s*=\s*["\']([^"\']+)["\']',
    re.IGNORECASE,
)
TITLE_RE = re.compile(r"<title[^>]*>([^<]+)</title>", re.IGNORECASE | re.DOTALL)
H1_RE = re.compile(r"<h1[^>]*>([^<]+)</h1>", re.IGNORECASE | re.DOTALL)
# 個別 img タグから fallback (og:image が無い場合)
IMG_SRC_RE = re.compile(
    r'<img[^>]+(?:data-src|src)\s*=\s*["\']([^"\']+\.(?:jpg|jpeg|png|webp))["\']',
    re.IGNORECASE,
)

# 寸法抽出: 拡張機能側 parseDimensions と同じパターン
DIMS_WDH_RE = re.compile(
    r"[WwＷ幅]\s*([0-9.]+)\s*[×xX\s]*[DdＤ奥][行深]?\s*"
    r"([0-9.]+)\s*[×xX\s]*[HhＨ高][さ]?\s*([0-9.]+)\s*(mm|cm)?",
    re.IGNORECASE,
)
DIMS_TRIPLE_RE = re.compile(
    r"([0-9.]+)\s*[×xX]\s*([0-9.]+)\s*[×xX]\s*([0-9.]+)\s*(mm|cm)",
    re.IGNORECASE,
)


USER_AGENT = "Mozilla/5.0 (compatible; EC3DBridge/2.4; +https://github.com/5newold111/furniture-3d-modeling-)"


def _to_cm(value: float, unit: str | None) -> float:
    return value / 10 if unit and unit.lower() == "mm" else value


def _parse_dimensions(text: str) -> dict:
    """テキストから W×D×H を cm 単位で抽出。見つからなければ全 0。"""
    out = {"width_cm": 0.0, "depth_cm": 0.0, "height_cm": 0.0}
    m = DIMS_WDH_RE.search(text)
    if m:
        unit = m.group(4)
        return {
            "width_cm": _to_cm(float(m.group(1)), unit),
            "depth_cm": _to_cm(float(m.group(2)), unit),
            "height_cm": _to_cm(float(m.group(3)), unit),
        }
    m = DIMS_TRIPLE_RE.search(text)
    if m:
        unit = m.group(4)
        return {
            "width_cm": _to_cm(float(m.group(1)), unit),
            "depth_cm": _to_cm(float(m.group(2)), unit),
            "height_cm": _to_cm(float(m.group(3)), unit),
        }
    return out


def _absolute_url(maybe_relative: str, base_url: str) -> str:
    """相対 URL を絶対 URL に変換 (//cdn.example.com/x.jpg のようなケースも対応)"""
    if maybe_relative.startswith("http://") or maybe_relative.startswith("https://"):
        return maybe_relative
    parsed = urlparse(base_url)
    if maybe_relative.startswith("//"):
        return f"{parsed.scheme}:{maybe_relative}"
    if maybe_relative.startswith("/"):
        return f"{parsed.scheme}://{parsed.netloc}{maybe_relative}"
    return f"{parsed.scheme}://{parsed.netloc}/{maybe_relative.lstrip('/')}"


async def scrape_product_url(url: str) -> dict:
    """URL をフェッチして ProductData 形式の dict を返す。

    SSRF 防御済み (is_url_safe を通る)。
    抽出品質は最小限 (og:image / og:title / 簡易 dimension regex)。
    JS-rendered SPA や認証必須ページは扱えない。
    """
    safe, reason = is_url_safe(url)
    if not safe:
        raise PipelineError(
            ErrorCode.INVALID_INPUT,
            f"安全でない URL です: {reason}",
        )

    try:
        async with httpx.AsyncClient(
            timeout=30, follow_redirects=True, headers={"User-Agent": USER_AGENT}
        ) as client:
            response = await client.get(url)
    except httpx.HTTPError as e:
        raise PipelineError(ErrorCode.IMAGE_DOWNLOAD_FAILED, f"URL フェッチ失敗: {e}") from e

    if response.status_code != 200:
        raise PipelineError(
            ErrorCode.IMAGE_DOWNLOAD_FAILED,
            f"URL が {response.status_code} を返しました",
        )

    html = response.text
    parsed = urlparse(url)
    site = parsed.hostname or "unknown"

    # 商品名: og:title → h1 → <title> の順
    name = None
    for pat in (OG_TITLE_RE, H1_RE, TITLE_RE):
        m = pat.search(html)
        if m:
            name = re.sub(r"\s+", " ", m.group(1)).strip()
            if name:
                break
    if not name:
        name = "Untitled product"

    # 画像: og:image を front 候補に、追加で img タグから上位 4 件を other
    images = []
    seen = set()
    og = OG_IMAGE_RE.search(html)
    if og:
        u = _absolute_url(og.group(1), url)
        images.append({"url": u, "type": "front"})
        seen.add(u.split("?")[0])
    for m in IMG_SRC_RE.finditer(html):
        u = _absolute_url(m.group(1), url)
        key = u.split("?")[0]
        if key in seen or "logo" in u.lower() or "icon" in u.lower():
            continue
        seen.add(key)
        images.append({"url": u, "type": "other"})
        if len(images) >= 5:
            break

    dimensions = _parse_dimensions(html)

    logger.info(f"scrape_product_url: name={name!r} images={len(images)} dims={dimensions}")

    return {
        "product_name": name[:500],
        "source_url": url,
        "site": site,
        "dimensions": dimensions,
        "colors": [],
        "materials": [],
        "images": images,
        "category": "家具",
    }
