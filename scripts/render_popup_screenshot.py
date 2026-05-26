"""
README 用の popup スクリーンショットを Pillow で描画する。
Playwright ダウンロードが封じられた環境でも動く mockup ジェネレーター。
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "popup_screenshot.png"


def font(sz: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    p = "/usr/share/fonts/truetype/dejavu/" + (
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    )
    try:
        return ImageFont.truetype(p, sz)
    except Exception:
        return ImageFont.load_default()


def main():
    W, H = 410, 560
    img = Image.new("RGB", (W, H), "#fafafa")
    d = ImageDraw.Draw(img)
    pad = 14

    d.text((pad, pad), "EC3D-Bridge", fill="#333", font=font(16, bold=True))

    tab_y = pad + 28
    tab_w = (W - pad * 2) / 3
    for i, (label, active) in enumerate([("単発", True), ("一括", False), ("履歴", False)]):
        x = pad + tab_w * i
        d.text(
            (x + tab_w / 2 - 18, tab_y + 4),
            label,
            fill="#2c5364" if active else "#666",
            font=font(13, bold=active),
        )
        if active:
            d.rectangle([x + 6, tab_y + 28, x + tab_w - 6, tab_y + 30], fill="#2c5364")
    d.line([pad, tab_y + 32, W - pad, tab_y + 32], fill="#d6dbe1")

    btn_y = tab_y + 50
    d.rounded_rectangle([pad, btn_y, W - pad, btn_y + 38], radius=6, fill="#2c5364")
    d.text(
        (pad + 50, btn_y + 11),
        "この商品を3D化 → Homestylerへ",
        fill="white",
        font=font(13, bold=True),
    )

    sy = btn_y + 56
    d.text((pad, sy), "[2/4] 3Dモデルを生成しています...", fill="#555", font=font(12))

    pby = sy + 28
    d.rounded_rectangle([pad, pby, W - pad, pby + 6], radius=3, fill="#e6e9ee")
    d.rounded_rectangle(
        [pad, pby, pad + (W - pad * 2) // 2, pby + 6], radius=3, fill="#2c5364"
    )

    piy = pby + 18
    d.rounded_rectangle([pad, piy, W - pad, piy + 60], radius=4, fill="#eef2f7")
    d.text(
        (pad + 8, piy + 8),
        "ダイニングテーブル ノーチェ4 NA",
        fill="#1a1a1a",
        font=font(13, bold=True),
    )
    d.text((pad + 8, piy + 26), "W120 × D75 × H72cm", fill="#555", font=font(12))
    d.text((pad + 8, piy + 42), "画像: 3 枚", fill="#555", font=font(12))

    pvy = piy + 78
    d.rounded_rectangle([pad, pvy, W - pad, pvy + 200], radius=6, fill="#1a1a1a")
    d.text((W // 2 - 50, pvy + 90), "🪑 3D Preview", fill="#888", font=font(13))
    d.text(
        (W // 2 - 90, pvy + 110),
        "model-viewer (auto-rotate)",
        fill="#666",
        font=font(10),
    )

    d.text(
        (pad, H - 24),
        "Powered by FastAPI + Playwright + Tripo3D + Blender",
        fill="#999",
        font=font(9),
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
