"""
実 Blender バイナリを呼ぶ統合テスト。
Blender が PATH (BLENDER_PATH) で見つからない場合はスキップする。

scale_model.py の Blender API 互換性 (例: Blender 4.0+ で
export_selected が削除されたなど) を回帰検出するため、
ユニットテスト (subprocess.run をモック) ではなく実走させる価値がある。
"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

BLENDER = shutil.which(os.getenv("BLENDER_PATH", "blender"))
pytestmark = pytest.mark.skipif(
    BLENDER is None,
    reason="Blender が PATH / BLENDER_PATH に見つかりません (CI / 開発機にインストール要)",
)


def _make_cube_glb(path: str, size_m: float = 0.2) -> None:
    subprocess.run(
        [
            BLENDER,
            "--background",
            "--python-expr",
            f"import bpy; bpy.ops.wm.read_factory_settings(use_empty=True);"
            f" bpy.ops.mesh.primitive_cube_add(size={size_m});"
            f" bpy.ops.export_scene.gltf(filepath='{path}', export_format='GLB')",
        ],
        capture_output=True,
        timeout=60,
        check=True,
    )


def _measure_glb(path: str) -> tuple[float, float, float]:
    """GLB の寸法を cm 単位で返す"""
    result = subprocess.run(
        [
            BLENDER,
            "--background",
            "--python-expr",
            f"import bpy; bpy.ops.wm.read_factory_settings(use_empty=True);"
            f" bpy.ops.import_scene.gltf(filepath='{path}');"
            f" o = next(x for x in bpy.context.scene.objects if x.type=='MESH');"
            f" print(f'_DIMS {{o.dimensions.x*100:.4f}} {{o.dimensions.y*100:.4f}} {{o.dimensions.z*100:.4f}}')",
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=True,
    )
    for line in result.stdout.splitlines():
        if line.startswith("_DIMS"):
            _, x, y, z = line.split()
            return float(x), float(y), float(z)
    raise AssertionError(f"_DIMS が見つからない:\n{result.stdout}")


def test_scale_model_actually_resizes_cube(tmp_path):
    """20cm 立方体 → 80x40x75cm に補正されること"""
    raw = str(tmp_path / "raw.glb")
    scaled = str(tmp_path / "scaled.glb")
    _make_cube_glb(raw, size_m=0.2)

    script = Path(__file__).resolve().parents[1] / "scripts" / "scale_model.py"
    result = subprocess.run(
        [BLENDER, "--background", "--python", str(script), "--", raw, scaled, "80", "40", "75"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, (
        f"Blender 失敗\nstdout: {result.stdout[-500:]}\nstderr: {result.stderr[-500:]}"
    )
    assert Path(scaled).exists(), "scaled GLB が出力されていない"

    x, y, z = _measure_glb(scaled)
    assert abs(x - 80) < 0.5, f"width: 期待 80cm, 実測 {x}cm"
    assert abs(y - 40) < 0.5, f"depth: 期待 40cm, 実測 {y}cm"
    assert abs(z - 75) < 0.5, f"height: 期待 75cm, 実測 {z}cm"


def test_scale_correction_service_invokes_blender(tmp_path, monkeypatch):
    """services.scale_correction.apply_real_scale を実 Blender 越しに実走"""
    from services.scale_correction import apply_real_scale

    monkeypatch.chdir(tmp_path)
    raw = str(tmp_path / "test_raw.glb")
    _make_cube_glb(raw, size_m=0.5)  # 50cm cube

    result = apply_real_scale(raw, 100, 50, 200)
    assert result.endswith("_scaled.glb")
    assert Path(result).exists()

    x, y, z = _measure_glb(result)
    assert abs(x - 100) < 0.5
    assert abs(y - 50) < 0.5
    assert abs(z - 200) < 0.5
