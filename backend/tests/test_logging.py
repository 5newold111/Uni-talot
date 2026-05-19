"""
JSON ログフォーマッタの動作検証。
"""

import json
import logging

from services.logging_config import JsonFormatter


def test_json_formatter_outputs_valid_json():
    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="hello world",
        args=(),
        exc_info=None,
    )
    out = formatter.format(record)
    payload = json.loads(out)
    assert payload["level"] == "INFO"
    assert payload["logger"] == "test"
    assert payload["message"] == "hello world"
    assert "ts" in payload


def test_json_formatter_includes_extra_fields():
    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.WARNING,
        pathname=__file__,
        lineno=10,
        msg="warn",
        args=(),
        exc_info=None,
    )
    record.job_id = "abc123"
    record.error_code = "model_quota_exceeded"
    payload = json.loads(formatter.format(record))
    assert payload["job_id"] == "abc123"
    assert payload["error_code"] == "model_quota_exceeded"


def test_json_formatter_handles_exception():
    formatter = JsonFormatter()
    try:
        raise ValueError("boom")
    except ValueError:
        import sys

        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname=__file__,
            lineno=10,
            msg="failed",
            args=(),
            exc_info=sys.exc_info(),
        )
    payload = json.loads(formatter.format(record))
    assert "ValueError" in payload["exception"]
    assert "boom" in payload["exception"]


def test_json_formatter_handles_non_serializable_extra():
    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="m",
        args=(),
        exc_info=None,
    )
    record.complex = object()  # not JSON-serializable
    payload = json.loads(formatter.format(record))  # must not raise
    assert "complex" in payload
