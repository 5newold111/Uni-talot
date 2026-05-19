"""
ログ設定。`LOG_FORMAT=json` で本番運用向けの構造化 JSON ログに切替可能。

開発時はデフォルトの人間可読フォーマット。Docker Compose / Kubernetes 等で
fluentd / Loki に流す場合は `LOG_FORMAT=json` を設定。
"""

import json
import logging
import os
import sys


class JsonFormatter(logging.Formatter):
    """1 行 1 JSON のシンプルなフォーマッタ。"""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # asctime/levelname/message 以外で interesting なフィールドがあれば追加
        for k, v in record.__dict__.items():
            if k in ("args", "exc_info", "exc_text", "stack_info"):
                continue
            if k.startswith("_"):
                continue
            if k in payload or k in (
                "name",
                "msg",
                "levelname",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "pathname",
                "filename",
                "module",
                "lineno",
                "funcName",
                "levelno",
            ):
                continue
            try:
                json.dumps(v)
                payload[k] = v
            except TypeError:
                payload[k] = repr(v)

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(log_file: str = "logs/app.log") -> None:
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    fmt = os.getenv("LOG_FORMAT", "text").lower()
    level = os.getenv("LOG_LEVEL", "INFO").upper()

    if fmt == "json":
        formatter: logging.Formatter = JsonFormatter()
    else:
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    # 既存ハンドラを削除して再設定 (uvicorn の reload 中の二重設定を防ぐ)
    root = logging.getLogger()
    root.setLevel(level)
    for h in list(root.handlers):
        root.removeHandler(h)

    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    root.addHandler(file_handler)
    root.addHandler(stream_handler)
