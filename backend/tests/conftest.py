import os
import sys
import tempfile

# テスト実行前に JOB_DB_PATH を一時ファイルに切り替える。
# 本番DB (./jobs.db) を汚さないため、また何度実行しても綺麗な状態から始まるため。
_TEST_DB_FD, _TEST_DB_PATH = tempfile.mkstemp(prefix="ec3d_test_", suffix=".db")
os.close(_TEST_DB_FD)
os.remove(_TEST_DB_PATH)  # JobManager が初期化時に作り直す
os.environ["JOB_DB_PATH"] = _TEST_DB_PATH

# レートリミットがテスト間で誤発火しないよう、テスト中は容量を緩める
os.environ.setdefault("RATE_LIMIT_BURST", "10000")
os.environ.setdefault("RATE_LIMIT_PER_SEC", "10000")

# backend/ ディレクトリを import path に追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_rate_limit_bucket():
    """各テスト前にレートリミットバケットをクリア (テスト間の干渉防止)"""
    try:
        import main

        # middleware_stack の RateLimitMiddleware を探してリセット
        stack = getattr(main.app, "middleware_stack", None)
        while stack is not None:
            if type(stack).__name__ == "RateLimitMiddleware":
                stack.bucket._buckets.clear()
                break
            stack = getattr(stack, "app", None)
    except Exception:
        pass
    yield
