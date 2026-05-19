import subprocess
from unittest.mock import patch

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


def test_invokes_blender_with_correct_args(tmp_path):
    raw = tmp_path / "abc_raw.glb"
    raw.write_bytes(b"GLB")
    expected_out = str(raw).replace("_raw.glb", "_scaled.glb")

    def fake_run(cmd, **kwargs):
        # Blender が成功した想定で出力ファイルを作る
        with open(expected_out, "wb") as f:
            f.write(b"SCALED")
        return subprocess.CompletedProcess(cmd, 0, stdout="ok", stderr="")

    with patch("services.scale_correction.subprocess.run", side_effect=fake_run) as m:
        out = apply_real_scale(str(raw), 80.0, 40.0, 75.0)

    assert out == expected_out
    cmd = m.call_args.args[0]
    # コマンド構造: blender --background --python <script> -- <in> <out> 80 40 75
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

    with patch("services.scale_correction.subprocess.run", side_effect=fake_run):
        try:
            apply_real_scale(str(raw), 80, 40, 75)
        except RuntimeError as e:
            assert "Blender" in str(e)
            return
        raise AssertionError("RuntimeError が発生するはず")
