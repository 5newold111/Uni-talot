"""カバーアート生成（プラガブル）。

デフォルトは依存ゼロの SVG プレースホルダーを生成する。
実運用では画像生成 API（Gemini 画像 / Stable Diffusion 等）に差し替え可能。
DistroKid は 3000x3000 px の JPG/PNG を要求するため、本番では PNG/JPG 化が必要。
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from .models import Album


def _color_from(text: str, salt: str = "") -> str:
    h = hashlib.md5((salt + text).encode("utf-8")).hexdigest()
    return f"#{h[:6]}"


class CoverArtGenerator:
    """SVG ベースのプレースホルダーカバーを生成する。"""

    def generate(self, album: Album, out_path: Path, artist: str = "AI Sound Lab") -> Path:
        c1 = _color_from(album.title, "a")
        c2 = _color_from(album.title, "b")
        title = _escape(album.title)
        artist_e = _escape(artist)
        svg = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="3000" height="3000" viewBox="0 0 3000 3000">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{c1}"/>
      <stop offset="100%" stop-color="{c2}"/>
    </linearGradient>
  </defs>
  <rect width="3000" height="3000" fill="url(#g)"/>
  <circle cx="1500" cy="1200" r="520" fill="#ffffff" fill-opacity="0.12"/>
  <text x="1500" y="1700" font-family="Helvetica, Arial, sans-serif" font-size="180"
        font-weight="bold" fill="#ffffff" text-anchor="middle">{title}</text>
  <text x="1500" y="1920" font-family="Helvetica, Arial, sans-serif" font-size="96"
        fill="#ffffff" fill-opacity="0.85" text-anchor="middle">{artist_e}</text>
</svg>
"""
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(svg, encoding="utf-8")
        return out_path


def _escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
