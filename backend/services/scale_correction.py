import subprocess
import os
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

BLENDER = os.getenv("BLENDER_PATH", "blender")
SCRIPT = os.path.join(os.path.dirname(__file__), "../scripts/scale_model.py")


def apply_real_scale(glb_path: str, width_cm: float, depth_cm: float, height_cm: float) -> str:
    """
    Blender CLI を使って GLB の実寸スケール補正を行う。
    寸法のいずれかが 0 の場合はスケール補正をスキップして元ファイルを返す。
    """
    if width_cm <= 0 or depth_cm <= 0 or height_cm <= 0:
        logger.warning("寸法情報が不完全なためスケール補正をスキップします")
        return glb_path

    output_path = glb_path.replace("_raw.glb", "_scaled.glb")

    cmd = [
        BLENDER, "--background", "--python", os.path.abspath(SCRIPT),
        "--",
        os.path.abspath(glb_path),
        os.path.abspath(output_path),
        str(width_cm),
        str(depth_cm),
        str(height_cm)
    ]

    logger.info(f"Blender 実行: {' '.join(cmd)}")

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=90
    )

    if result.stdout:
        logger.info(f"[Blender stdout]\n{result.stdout}")
    if result.stderr:
        logger.warning(f"[Blender stderr]\n{result.stderr[-1000:]}")

    if result.returncode != 0:
        raise RuntimeError(
            f"Blenderスクリプトがエラーで終了しました (code={result.returncode})\n"
            f"stderr末尾: {result.stderr[-500:]}"
        )

    if not os.path.exists(output_path):
        raise RuntimeError(f"スケール補正後のファイルが生成されませんでした: {output_path}")

    logger.info(f"スケール補正完了: {output_path}")
    return output_path
