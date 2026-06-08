"""カバーアート生成（プラガブル・バックエンド方式）。

バックエンド:
  - "gemini": Gemini の画像生成で抽象的アートワークを作り、PIL で
              3000x3000 に整形してタイトル/アーティストを重ねる。失敗時はローカルへ。
  - "local":  Pillow があれば 3000x3000 PNG、無ければ依存ゼロの SVG。
  - "auto":   Gemini が使えれば gemini、なければ local（既定）。

著作権セーフ:
  画像プロンプトは抽象的なアートワークに限定し、実在の人物・ロゴ・既存作品・
  アーティストを参照しない。
"""

from __future__ import annotations

import hashlib
import io
import logging
from pathlib import Path

from .config import Settings
from .models import Album

logger = logging.getLogger(__name__)

SIZE = 3000  # DistroKid 要件: 3000x3000


# ── 共通ユーティリティ ──
def _rgb_from(text: str, salt: str = "") -> tuple[int, int, int]:
    h = hashlib.md5((salt + text).encode("utf-8")).hexdigest()
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _hex_from(text: str, salt: str = "") -> str:
    r, g, b = _rgb_from(text, salt)
    return f"#{r:02x}{g:02x}{b:02x}"


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


def _overlay_title(img, title: str, artist: str):
    """PIL Image にタイトル/アーティストを下部へ重ね、3000x3000 に整える。"""
    from PIL import Image, ImageDraw, ImageEnhance

    img = img.convert("RGB").resize((SIZE, SIZE))
    # 下部に可読性確保のための半透明グラデを敷く
    overlay = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.rectangle((0, int(SIZE * 0.66), SIZE, SIZE), fill=(0, 0, 0, 110))
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

    draw = ImageDraw.Draw(img)
    _draw_centered(draw, title, SIZE // 2, int(SIZE * 0.80), _load_font(180), (255, 255, 255))
    _draw_centered(draw, artist, SIZE // 2, int(SIZE * 0.88), _load_font(96), (230, 230, 230))
    return img


# ── ローカル生成（Pillow → SVG フォールバック）──
class LocalCoverArtGenerator:
    def generate(self, album: Album, out_dir: Path, artist: str = "AI Sound Lab",
                 style_hint: str = "") -> Path:
        out_dir.mkdir(parents=True, exist_ok=True)
        try:
            from PIL import Image  # noqa: F401

            return self._png(album, out_dir / "cover.png", artist)
        except Exception as exc:
            logger.info("PNG cover unavailable (%s); generating SVG fallback", exc)
            return self._svg(album, out_dir / "cover.svg", artist)

    def _png(self, album: Album, out_path: Path, artist: str) -> Path:
        from PIL import Image, ImageDraw

        c1 = _rgb_from(album.title, "a")
        c2 = _rgb_from(album.title, "b")
        # 縦方向グラデ（NumPy 不要、行単位で高速生成）
        grad = Image.new("RGB", (1, SIZE))
        for y in range(SIZE):
            t = y / (SIZE - 1)
            grad.putpixel((0, y), tuple(int(c1[i] * (1 - t) + c2[i] * t) for i in range(3)))
        img = grad.resize((SIZE, SIZE))

        draw = ImageDraw.Draw(img)
        draw.ellipse((SIZE * 0.27, SIZE * 0.18, SIZE * 0.73, SIZE * 0.55),
                     outline=(255, 255, 255), width=12)
        _draw_centered(draw, album.title, SIZE // 2, int(SIZE * 0.62), _load_font(180), (255, 255, 255))
        _draw_centered(draw, artist, SIZE // 2, int(SIZE * 0.70), _load_font(96), (235, 235, 235))
        img.save(out_path, "PNG")
        return out_path

    def _svg(self, album: Album, out_path: Path, artist: str) -> Path:
        c1, c2 = _hex_from(album.title, "a"), _hex_from(album.title, "b")
        title, artist_e = _escape(album.title), _escape(artist)
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


# ── Gemini 画像生成 ──
class GeminiCoverArtGenerator:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.cover_cfg = settings.section("cover")
        self.model_name = self.cover_cfg.get("model", "gemini-2.0-flash-preview-image-generation")
        self._fallback = LocalCoverArtGenerator()

    def generate(self, album: Album, out_dir: Path, artist: str = "AI Sound Lab",
                 style_hint: str = "") -> Path:
        out_dir.mkdir(parents=True, exist_ok=True)
        try:
            png_bytes = self._render(album, style_hint)
            from PIL import Image

            img = Image.open(io.BytesIO(png_bytes))
            try:
                img = _overlay_title(img, album.title, artist)
            except Exception:  # PIL のフォント等が無ければ素の画像を使う
                img = img.convert("RGB").resize((SIZE, SIZE))
            out_path = out_dir / "cover.png"
            img.save(out_path, "PNG")
            logger.info("Gemini cover generated -> %s", out_path)
            return out_path
        except Exception as exc:
            logger.warning("Gemini cover failed (%s); falling back to local", exc)
            return self._fallback.generate(album, out_dir, artist, style_hint)

    def _build_prompt(self, album: Album, style_hint: str) -> str:
        return (
            "Abstract album cover artwork. "
            f"Visual mood inspired by: {style_hint or 'modern electronic music'}. "
            "Bold composition, rich color, atmospheric, square 1:1. "
            "No text, no words, no logos, no real people, no brand marks. "
            "Original artwork only; do not depict or imitate any existing artwork or artist."
        )

    def _render(self, album: Album, style_hint: str) -> bytes:
        import google.generativeai as genai

        genai.configure(api_key=self.settings.gemini_api_key)
        model = genai.GenerativeModel(self.model_name)
        prompt = self._build_prompt(album, style_hint)
        # 画像対応モデルは inline_data（画像バイト）を parts に返す
        resp = model.generate_content(
            prompt,
            generation_config={"response_modalities": ["TEXT", "IMAGE"]},
        )
        for cand in getattr(resp, "candidates", []) or []:
            for part in getattr(cand.content, "parts", []) or []:
                inline = getattr(part, "inline_data", None)
                if inline and getattr(inline, "data", None):
                    return inline.data
        raise RuntimeError("No image data returned by Gemini image model")


# ── 後方互換エイリアス & ファクトリ ──
class CoverArtGenerator(LocalCoverArtGenerator):
    """既定（ローカル）。後方互換のため名前を維持。"""


def create_cover_generator(settings: Settings):
    """設定 (cover.backend) と認証状態に基づきバックエンドを選ぶ。"""
    backend = (settings.section("cover").get("backend") or "auto").lower()
    if backend == "local":
        return LocalCoverArtGenerator()
    if backend == "gemini":
        return GeminiCoverArtGenerator(settings)
    # auto
    if not settings.gemini_mock:
        return GeminiCoverArtGenerator(settings)
    return LocalCoverArtGenerator()


def _escape(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
