import subprocess
from unittest.mock import patch

import pytest

from services.errors import ErrorCode, PipelineError
from services.scale_correction import apply_real_scale


def test_skips_when_any_dimension_is_zero(tmp_path):
    glb = tmp_path / "model_raw.glb"
    glb.write_bytes(b"GLB")
    # 寸法0なら Blender を呼ばずに元パスを返す
    result = apply_real_scale(str(glb), 0, 40, 75)
    assert result == str(glb)
    result = apply_real_scale(str(glb), 80, 0, 75)
    assert result == str(glb)
    result = apply_real_scale(str(glb), 80, 40, 0)
    assert result == str(glb)


def test_raises_when_blender_not_found(tmp_path):
    raw = tmp_path / "abc_raw.glb"
    raw.write_bytes(b"GLB")
    with patch("services.scale_correction.shutil.which", return_value=None):
        with patch("services.scale_correction.os.path.isfile", return_value=False):
            with pytest.raises(PipelineError) as exc:
                apply_real_scale(str(raw), 80, 40, 75)
    assert exc.value.code == ErrorCode.BLENDER_NOT_FOUND


def test_invokes_blender_with_correct_args(tmp_path):
    raw = tmp_path / "abc_raw.glb"
    raw.write_bytes(b"GLB")
    expected_out = str(raw).replace("_raw.glb", "_scaled.glb")

    def fake_run(cmd, **kwargs):
        with open(expected_out, "wb") as f:
            f.write(b"SCALED")
        return subprocess.CompletedProcess(cmd, 0, stdout="ok", stderr="")

    with (
        patch("services.scale_correction.shutil.which", return_value="/fake/blender"),
        patch("services.scale_correction.subprocess.run", side_effect=fake_run) as m,
    ):
        out = apply_real_scale(str(raw), 80.0, 40.0, 75.0)

    assert out == expected_out
    cmd = m.call_args.args[0]
    assert cmd[0] == "/fake/blender"
    assert "--background" in cmd
    assert "--python" in cmd
    assert "--" in cmd
    sep = cmd.index("--")
    user_args = cmd[sep + 1 :]
    assert user_args[0].endswith("abc_raw.glb")
    assert user_args[1].endswith("abc_scaled.glb")
    assert user_args[2:5] == ["80.0", "40.0", "75.0"]


def test_raises_when_blender_fails(tmp_path):
    raw = tmp_path / "x_raw.glb"
    raw.write_bytes(b"GLB")

    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="boom")

    with (
        patch("services.scale_correction.shutil.which", return_value="/fake/blender"),
        patch("services.scale_correction.subprocess.run", side_effect=fake_run),
    ):
        with pytest.raises(PipelineError) as exc:
            apply_real_scale(str(raw), 80, 40, 75)
    assert exc.value.code == ErrorCode.SCALE_FAILED
    assert "Blender" in exc.value.message
