"""
output/ ディレクトリの古いファイルを定期的に削除するユーティリティ。
"""

import logging
import os
import time

logger = logging.getLogger(__name__)


def cleanup_output(directory: str = "output", max_age_seconds: int = 7 * 24 * 3600) -> int:
    """
    指定ディレクトリ配下の max_age_seconds より古いファイルを削除する。
    削除したファイル数を返す。例外が起きても黙って次へ進む（best-effort）。
    """
    if not os.path.isdir(directory):
        return 0

    cutoff = time.time() - max_age_seconds
    removed = 0
    for name in os.listdir(directory):
        path = os.path.join(directory, name)
        try:
            if not os.path.isfile(path):
                continue
            if os.path.getmtime(path) < cutoff:
                os.remove(path)
                removed += 1
        except OSError as e:
            logger.warning(f"cleanup: 削除失敗 {path}: {e}")
    if removed:
        logger.info(f"cleanup: {removed} 件の古いファイルを削除 ({directory})")
    return removed
