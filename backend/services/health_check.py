"""
依存コンポーネントの状態を検査するヘルスチェック。
"""
import os
import shutil
import subprocess
from dotenv import load_dotenv

load_dotenv()


def _check_blender() -> dict:
    blender = os.getenv("BLENDER_PATH", "blender")
    path = shutil.which(blender) or (blender if os.path.isfile(blender) else None)
    if not path:
        return {"ok": False, "detail": f"Blender が見つかりません (path={blender})"}
    try:
        result = subprocess.run(
            [path, "--version"], capture_output=True, text=True, timeout=10
        )
        version = result.stdout.strip().split("\n", 1)[0] if result.stdout else "unknown"
        return {"ok": result.returncode == 0, "detail": version, "path": path}
    except Exception as e:
        return {"ok": False, "detail": f"Blender 実行エラー: {e}", "path": path}


def _check_3d_provider() -> dict:
    key = os.getenv("FAL_API_KEY", "")
    ok = bool(key) and key != "your_fal_api_key_here"
    return {
        "ok": ok,
        "provider": "tripo",
        "detail": "FAL_API_KEY 設定済み" if ok else "FAL_API_KEY 未設定",
    }


def _check_homestyler() -> dict:
    email = os.getenv("HOMESTYLER_EMAIL", "")
    password = os.getenv("HOMESTYLER_PASSWORD", "")
    placeholders = {"your_email_here", "your_password_here", ""}
    ok = email not in placeholders and password not in placeholders
    return {"ok": ok, "detail": "認証情報 設定済み" if ok else "HOMESTYLER_EMAIL/PASSWORD 未設定"}


def collect_health() -> dict:
    """
    依存コンポーネント全体の状態を集約して返す。
    components の全てが ok のとき status='ok'、ひとつでも欠ければ 'degraded'。
    """
    components = {
        "blender": _check_blender(),
        "model_provider": _check_3d_provider(),
        "homestyler": _check_homestyler(),
    }
    overall_ok = all(c["ok"] for c in components.values())
    return {
        "status": "ok" if overall_ok else "degraded",
        "components": components,
    }
