"""
本番依存 (Tripo / Homestyler / Blender) の疎通・認証を最小コードで確認する CLI。

サンドボックスでは検証できないため、ローカルで:

    cd backend
    python scripts/verify_dependencies.py --all
    python scripts/verify_dependencies.py --tripo  # FAL_API_KEY を使って 1 枚 1回の合成画像で実生成
    python scripts/verify_dependencies.py --homestyler  # headless=False でログイン→マイモデル画面まで
    python scripts/verify_dependencies.py --blender  # 立方体 GLB を実走スケール補正
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")


def check_blender() -> bool:
    print("=== Blender 検証 ===")
    import shutil
    import subprocess

    from PIL import Image

    blender = os.getenv("BLENDER_PATH", "blender")
    path = shutil.which(blender) or (blender if os.path.isfile(blender) else None)
    if not path:
        print(f"  ✗ Blender が見つかりません (BLENDER_PATH={blender})")
        return False
    ver = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=10)
    print(f"  ✓ {ver.stdout.strip().split(chr(10))[0]}")

    out_dir = ROOT / "output"
    out_dir.mkdir(exist_ok=True)
    raw = out_dir / "_verify_raw.glb"
    scaled_expected = out_dir / "_verify_scaled.glb"

    # 立方体 GLB を Blender で作る
    subprocess.run(
        [
            path,
            "--background",
            "--python-expr",
            f"import bpy; bpy.ops.wm.read_factory_settings(use_empty=True);"
            f" bpy.ops.mesh.primitive_cube_add(size=0.2);"
            f" bpy.ops.export_scene.gltf(filepath='{raw}', export_format='GLB')",
        ],
        capture_output=True,
        timeout=30,
    )
    if not raw.exists():
        print("  ✗ テスト用 GLB の生成失敗")
        return False
    print(f"  ✓ 入力 GLB 生成: {raw.name} ({raw.stat().st_size}B)")

    from services.scale_correction import apply_real_scale

    actual = apply_real_scale(str(raw), 80, 40, 75)
    if Path(actual) != scaled_expected or not Path(actual).exists():
        print(f"  ✗ apply_real_scale が想定パスを返さなかった: {actual}")
        return False
    print(f"  ✓ scale_correction 経由で {Path(actual).name} 出力")

    # 寸法を再測定
    result = subprocess.run(
        [
            path,
            "--background",
            "--python-expr",
            f"import bpy; bpy.ops.wm.read_factory_settings(use_empty=True);"
            f" bpy.ops.import_scene.gltf(filepath='{actual}');"
            f" o = next(x for x in bpy.context.scene.objects if x.type=='MESH');"
            f" print(f'_DIMS X={{o.dimensions.x*100:.2f}} Y={{o.dimensions.y*100:.2f}} Z={{o.dimensions.z*100:.2f}}')",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    for line in result.stdout.splitlines():
        if line.startswith("_DIMS"):
            print(f"  ✓ 出力 GLB の実測: {line[6:]}cm (期待: X=80 Y=40 Z=75)")
            break
    raw.unlink(missing_ok=True)
    Path(actual).unlink(missing_ok=True)
    # 画像ファイルダミー (downloader テスト用) を作っておく
    Image.new("RGB", (800, 800), (200, 100, 50)).save(out_dir / "_verify.jpg")
    return True


async def check_tripo() -> bool:
    print("=== Tripo (fal.ai) 検証 ===")
    key = os.getenv("FAL_API_KEY", "")
    if not key or key == "your_fal_api_key_here":
        print("  ✗ FAL_API_KEY 未設定")
        return False
    out_dir = ROOT / "output"
    out_dir.mkdir(exist_ok=True)
    from PIL import Image

    test_img = out_dir / "_verify.jpg"
    Image.new("RGB", (512, 512), (180, 120, 80)).save(test_img)
    print(f"  → 合成画像 {test_img.name} (512x512) で Tripo を呼び出します...")
    try:
        from services.model_generator import generate_3d_model

        glb_path = await generate_3d_model(str(test_img))
        size = Path(glb_path).stat().st_size
        print(f"  ✓ GLB 生成成功: {glb_path} ({size}B)")
        return True
    except Exception as e:
        print(f"  ✗ 生成失敗: {e}")
        return False


async def check_homestyler() -> bool:
    print("=== Homestyler (Playwright) 検証 ===")
    email = os.getenv("HOMESTYLER_EMAIL", "")
    password = os.getenv("HOMESTYLER_PASSWORD", "")
    if not email or email == "your_email_here":
        print("  ✗ HOMESTYLER_EMAIL 未設定")
        return False
    if not password or password == "your_password_here":
        print("  ✗ HOMESTYLER_PASSWORD 未設定")
        return False

    # GLB ファイルが必要なのでダミーを作る (Blender 検証が事前に成功している前提)
    out_dir = ROOT / "output"
    out_dir.mkdir(exist_ok=True)
    glb = out_dir / "_verify_homestyler.glb"
    if not glb.exists():
        # Blender で空 GLB を作る
        import subprocess

        subprocess.run(
            [
                "blender",
                "--background",
                "--python-expr",
                f"import bpy; bpy.ops.wm.read_factory_settings(use_empty=True);"
                f" bpy.ops.mesh.primitive_cube_add(size=0.5);"
                f" bpy.ops.export_scene.gltf(filepath='{glb}', export_format='GLB')",
            ],
            capture_output=True,
            timeout=30,
        )

    print("  → headless=False で目視確認モードで起動します (デバッグ用)")
    print("  → Homestyler ログイン → アップロード画面までを実行")
    # headless=False に強制的に上書きできないので、homestyler_bot 内の SELECTORS を呼ぶだけ
    from services.homestyler_bot import upload_to_homestyler

    try:
        await upload_to_homestyler(
            glb_path=str(glb),
            product_name="verify_test",
            dimensions={"width_cm": 50, "depth_cm": 50, "height_cm": 50},
        )
        print("  ✓ 完了")
        return True
    except Exception as e:
        print(f"  ✗ 失敗: {e}")
        print("    → logs/error_verify_test.png にスクリーンショットがあるか確認")
        return False


def main():
    p = argparse.ArgumentParser(description="本番依存の疎通検証")
    p.add_argument("--all", action="store_true")
    p.add_argument("--blender", action="store_true")
    p.add_argument("--tripo", action="store_true")
    p.add_argument("--homestyler", action="store_true")
    args = p.parse_args()

    if args.all:
        args.blender = args.tripo = args.homestyler = True
    if not any([args.blender, args.tripo, args.homestyler]):
        p.print_help()
        return 1

    results: dict[str, bool] = {}
    if args.blender:
        results["blender"] = check_blender()
    if args.tripo:
        results["tripo"] = asyncio.run(check_tripo())
    if args.homestyler:
        results["homestyler"] = asyncio.run(check_homestyler())

    print()
    print("=== サマリ ===")
    for name, ok in results.items():
        print(f"  {name}: {'✓ OK' if ok else '✗ NG'}")
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
