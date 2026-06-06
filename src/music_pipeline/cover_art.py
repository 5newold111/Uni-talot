"""カバーアート生成（プラガブル）。

優先度:
  1. Pillow があれば 3000x3000 の PNG を生成（DistroKid の要件を満たす）。
  2. 無ければ依存ゼロの SVG プレースホルダーを生成。

実運用では `ImageCoverArtGenerator` を画像生成 API（Gemini 画像 / Stable
Diffusion 等）の実装に差し替え可能。
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from .models import Album

logger = logging.getLogger(__name__)

SIZE = 3000  # DistroKid 要件: 3000x3000


def _rgb_from(text: str, salt: str = "") -> tuple[int, int, int]:
    h = hashlib.md5((salt + text).encode("utf-8")).hexdigest()
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _hex_from(text: str, salt: str = "") -> str:
    r, g, b = _rgb_from(text, salt)
    return f"#{r:02x}{g:02x}{b:02x}"


class CoverArtGenerator:
    """利用可能なバックエンドで最良のカバーを生成するファサード。"""

    def generate(self, album: Album, out_dir: Path, artist: str = "AI Sound Lab") -> Path:
        out_dir.mkdir(parents=True, exist_ok=True)
        try:
            from PIL import Image  # noqa: F401

            return _generate_png(album, out_dir / "cover.png", artist)
        except Exception as exc:  # Pillow 未導入など
            logger.info("PNG cover unavailable (%s); generating SVG fallback", exc)
            return _generate_svg(album, out_dir / "cover.svg", artist)


def _generate_png(album: Album, out_path: Path, artist: str) -> Path:
    from PIL import Image, ImageDraw, ImageFont

    c1 = _rgb_from(album.title, "a")
    c2 = _rgb_from(album.title, "b")

    # 斜め線形グラデーション
    base = Image.new("RGB", (SIZE, SIZE), c1)
    top = Image.new("RGB", (SIZE, SIZE), c2)
    mask = Image.new("L", (SIZE, SIZE))
    mask_px = mask.load()
    for y in range(SIZE):
        # 行ごとに 0..255（縦方向グラデで十分な見栄え、計算は軽量）
        v = int(255 * y / (SIZE - 1))
        for x in range(0, SIZE, 8):  # 8px ステップで高速化
            for xx in range(x, min(x + 8, SIZE)):
                mask_px[xx, y] = v
    img = Image.composite(top, base, mask)

    draw = ImageDraw.Draw(img)
    # 装飾円
    draw.ellipse((SIZE * 0.27, SIZE * 0.18, SIZE * 0.73, SIZE * 0.55), fill=None,
                 outline=(255, 255, 255), width=12)

    title_font = _load_font(180)
    artist_font = _load_font(96)
    _draw_centered(draw, album.title, SIZE // 2, int(SIZE * 0.62), title_font, (255, 255, 255))
    _draw_centered(draw, artist, SIZE // 2, int(SIZE * 0.70), artist_font, (235, 235, 235))

    img.save(out_path, "PNG")
    return out_path


def _load_font(size: int):
    from PIL import ImageFont

    for name in ("DejaVuSans-Bold.ttf", "DejaVuSans.ttf", "Arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _draw_centered(draw, text: str, cx: int, cy: int, font, fill) -> None:
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    except Exception:
        w, h = draw.textlength(text, font=font), font.size
    draw.text((cx - w / 2, cy - h / 2), text, font=font, fill=fill)


def _generate_svg(album: Album, out_path: Path, artist: str) -> Path:
    c1 = _hex_from(album.title, "a")
    c2 = _hex_from(album.title, "b")
    title = _escape(album.title)
    artist_e = _escape(artist)
    svg = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{SIZE}" height="{SIZE}" viewBox="0 0 {SIZE} {SIZE}">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{c1}"/>
      <stop offset="100%" stop-color="{c2}"/>
    </linearGradient>
  </defs>
  <rect width="{SIZE}" height="{SIZE}" fill="url(#g)"/>
  <circle cx="1500" cy="1200" r="520" fill="#ffffff" fill-opacity="0.12"/>
  <text x="1500" y="1700" font-family="Helvetica, Arial, sans-serif" font-size="180"
        font-weight="bold" fill="#ffffff" text-anchor="middle">{title}</text>
  <text x="1500" y="1920" font-family="Helvetica, Arial, sans-serif" font-size="96"
        fill="#ffffff" fill-opacity="0.85" text-anchor="middle">{artist_e}</text>
</svg>
"""
    out_path.write_text(svg, encoding="utf-8")
    return out_path


def _escape(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
