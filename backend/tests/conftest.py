import os
import sys
import tempfile

# テスト実行前に JOB_DB_PATH を一時ファイルに切り替える。
# 本番DB (./jobs.db) を汚さないため、また何度実行しても綺麗な状態から始まるため。
_TEST_DB_FD, _TEST_DB_PATH = tempfile.mkstemp(prefix="ec3d_test_", suffix=".db")
os.close(_TEST_DB_FD)
os.remove(_TEST_DB_PATH)  # JobManager が初期化時に作り直す
os.environ["JOB_DB_PATH"] = _TEST_DB_PATH

# backend/ ディレクトリを import path に追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
