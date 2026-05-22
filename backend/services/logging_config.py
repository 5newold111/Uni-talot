"""
ログ設定。`LOG_FORMAT=json` で本番運用向けの構造化 JSON ログに切替可能。

開発時はデフォルトの人間可読フォーマット。Docker Compose / Kubernetes 等で
fluentd / Loki に流す場合は `LOG_FORMAT=json` を設定。
"""

import json
import logging
import os
import re
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


# ログから機密値を自動マスクするフィルター。
# .env から読んだ実値そのものがログ文字列に登場した場合に <REDACTED:NAME> に置換する。
# 「漏洩しないように書く」のが第一原則だが、ヒューマンエラー時の最終防衛線として動かす。
_SECRET_ENV_VARS = (
    "FAL_API_KEY",
    "HOMESTYLER_PASSWORD",
    "EC3D_API_KEY",
    "HF_TOKEN",  # 念のため過去互換
)


class SecretRedactor(logging.Filter):
    """各レコードのメッセージから既知シークレット値を <REDACTED:NAME> に置換する。"""

    def __init__(self) -> None:
        super().__init__()
        # value が短すぎる/プレースホルダの場合はパターンに含めない
        self._patterns: list[tuple[re.Pattern, str]] = []
        for name in _SECRET_ENV_VARS:
            val = os.getenv(name, "")
            if (
                val
                and len(val) >= 8
                and val not in ("your_fal_api_key_here", "your_password_here", "your_email_here")
            ):
                self._patterns.append((re.compile(re.escape(val)), f"<REDACTED:{name}>"))

    def filter(self, record: logging.LogRecord) -> bool:
        if not self._patterns:
            return True
        try:
            msg = record.getMessage()
        except Exception:
            return True
        masked = msg
        for pat, repl in self._patterns:
            masked = pat.sub(repl, masked)
        if masked != msg:
            # 後段で再フォーマットされないよう、args をクリアして msg を直接置換
            record.msg = masked
            record.args = ()
        return True


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

    # 機密値マスキング
    redactor = SecretRedactor()
    file_handler.addFilter(redactor)
    stream_handler.addFilter(redactor)

    root.addHandler(file_handler)
    root.addHandler(stream_handler)
