import os
import time

from services.cleanup import cleanup_output


def test_cleanup_returns_zero_for_missing_directory(tmp_path):
    assert cleanup_output(str(tmp_path / "nope")) == 0


def test_cleanup_removes_old_files_but_keeps_fresh_ones(tmp_path):
    old = tmp_path / "old.glb"
    new = tmp_path / "new.glb"
    old.write_bytes(b"x")
    new.write_bytes(b"y")

    # 古いファイルの mtime を 30 日前にする
    past = time.time() - 30 * 24 * 3600
    os.utime(old, (past, past))

    removed = cleanup_output(str(tmp_path), max_age_seconds=7 * 24 * 3600)
    assert removed == 1
    assert not old.exists()
    assert new.exists()


def test_cleanup_skips_subdirectories(tmp_path):
    subdir = tmp_path / "sub"
    subdir.mkdir()
    past = time.time() - 100 * 24 * 3600
    os.utime(subdir, (past, past))

    removed = cleanup_output(str(tmp_path), max_age_seconds=1)
    assert removed == 0
    assert subdir.exists()
