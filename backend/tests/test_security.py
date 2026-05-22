"""
セキュリティ対策の検証:
  - SSRF 防御 (internal/private IP への URL を弾く)
  - シークレット値のログマスキング
  - エラーメッセージから生 API レスポンスが流出しないこと
"""

import logging

import httpx
import pytest
import respx

from services import image_downloader, logging_config, model_generator
from services.errors import ErrorCode, PipelineError
from services.url_safety import is_url_safe

# ===== url_safety: SSRF 防御 =====


@pytest.mark.parametrize(
    "url,expected_block",
    [
        # 内部 IP に直接アクセス → 弾く
        ("http://127.0.0.1/x.jpg", True),
        ("http://169.254.169.254/latest/meta-data/", True),  # AWS metadata
        ("http://10.0.0.5/secret.jpg", True),
        ("http://192.168.1.1/admin", True),
        ("http://172.16.5.5/", True),
        ("http://[::1]/x", True),
        # スキームが http(s) 以外 → 弾く
        ("ftp://example.com/x.jpg", True),
        ("file:///etc/passwd", True),
        ("javascript:alert(1)", True),
        # 解決できないホスト → 弾く
        ("http://this-host-cannot-resolve.invalid/x.jpg", True),
    ],
)
def test_url_safety_blocks_dangerous(url: str, expected_block: bool):
    safe, reason = is_url_safe(url)
    assert safe is not expected_block, f"{url}: safe={safe}, reason={reason}"


def test_url_safety_allows_public_dns():
    # 1.1.1.1 (Cloudflare) や 8.8.8.8 を引くドメインは安全とみなす
    safe, reason = is_url_safe("http://1.1.1.1/")
    assert safe is True, reason


# ===== image_downloader が安全でない URL をスキップする =====


@respx.mock
async def test_image_downloader_skips_unsafe_urls(tmp_path, monkeypatch):
    """malicious な URL (内部 IP) を含む候補は無視して次の候補に進む"""
    monkeypatch.chdir(tmp_path)
    # http://127.0.0.1 は url_safety で弾かれるので httpx は呼ばれない
    # 全ての URL が unsafe ならエラーになる
    images = [
        {"url": "http://127.0.0.1/secret.jpg", "type": "front"},
        {"url": "http://169.254.169.254/aws-meta", "type": "other"},
    ]
    with pytest.raises(PipelineError) as exc:
        await image_downloader.download_main_image(images)
    assert exc.value.code == ErrorCode.IMAGE_DOWNLOAD_FAILED


# ===== logging: シークレットマスキング =====


def test_secret_redactor_masks_known_values(monkeypatch, caplog):
    monkeypatch.setenv("FAL_API_KEY", "sk-fal-supersecret12345")
    monkeypatch.setenv("EC3D_API_KEY", "ec3d-token-xyzabc789")
    redactor = logging_config.SecretRedactor()

    rec = logging.LogRecord(
        name="t",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="Calling Tripo with key=sk-fal-supersecret12345 and our key=ec3d-token-xyzabc789",
        args=(),
        exc_info=None,
    )
    redactor.filter(rec)
    msg = rec.getMessage()
    assert "sk-fal-supersecret12345" not in msg
    assert "ec3d-token-xyzabc789" not in msg
    assert "<REDACTED:FAL_API_KEY>" in msg
    assert "<REDACTED:EC3D_API_KEY>" in msg


def test_secret_redactor_does_nothing_when_env_empty(monkeypatch):
    monkeypatch.delenv("FAL_API_KEY", raising=False)
    monkeypatch.delenv("HOMESTYLER_PASSWORD", raising=False)
    monkeypatch.delenv("EC3D_API_KEY", raising=False)
    redactor = logging_config.SecretRedactor()
    rec = logging.LogRecord(
        name="t",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="plain message",
        args=(),
        exc_info=None,
    )
    redactor.filter(rec)
    assert rec.getMessage() == "plain message"


def test_secret_redactor_skips_placeholders(monkeypatch):
    """`.env.example` のプレースホルダ値は短いし無視されるべき"""
    monkeypatch.setenv("FAL_API_KEY", "your_fal_api_key_here")
    monkeypatch.setenv("HOMESTYLER_PASSWORD", "your_password_here")
    redactor = logging_config.SecretRedactor()
    rec = logging.LogRecord(
        name="t",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="hello your_password_here world",
        args=(),
        exc_info=None,
    )
    redactor.filter(rec)
    # プレースホルダはマスクされない (誤検知を避けるため)
    assert "your_password_here" in rec.getMessage()


def test_secret_redactor_skips_short_values(monkeypatch):
    """短すぎる値 (8文字未満) は誤検知が多いので無視"""
    monkeypatch.setenv("FAL_API_KEY", "short")
    redactor = logging_config.SecretRedactor()
    rec = logging.LogRecord(
        name="t",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="my short answer is short",
        args=(),
        exc_info=None,
    )
    redactor.filter(rec)
    assert rec.getMessage() == "my short answer is short"


# ===== model_generator: エラーメッセージから生レスポンスを除外 =====


@respx.mock
async def test_tripo_error_message_does_not_leak_response_body(tmp_path, monkeypatch):
    """Tripo が API key を含むエラーレスポンスを返した場合でも、
    PipelineError.message には生のレスポンス本文が含まれないこと。"""

    monkeypatch.setattr(model_generator, "FAL_KEY", "test-key")
    monkeypatch.chdir(tmp_path)

    # Tripo がトークン込みの sensitive な内容を返したと想定
    sensitive_body = (
        "Internal error: api_key=sk-leaked-12345 user_email=admin@internal.local "
        "stack trace at /usr/local/lib/.../auth.py:42"
    )
    respx.post("https://fal.run/fal-ai/tripo3d/v2.5/image-to-3d").mock(
        return_value=httpx.Response(500, text=sensitive_body)
    )

    img = tmp_path / "x.jpg"
    img.write_bytes(b"\xff\xd8" + b"jpeg")

    with pytest.raises(PipelineError) as exc:
        await model_generator.generate_3d_model(str(img))

    # ステータスコードは含まれるが、生 body は含まれない
    assert "500" in exc.value.message
    assert "sk-leaked-12345" not in exc.value.message
    assert "admin@internal.local" not in exc.value.message
    assert "auth.py" not in exc.value.message


# ===== gitignore に重要ファイルが入っているか =====


def test_critical_files_are_gitignored():
    """homestyler_storage_state.json と .env が gitignore に含まれていることを確認"""
    from pathlib import Path

    gitignore = Path(__file__).resolve().parents[1] / ".gitignore"
    content = gitignore.read_text(encoding="utf-8")
    assert ".env" in content
    assert "homestyler_storage_state.json" in content or "homestyler_*.json" in content
    assert "logs/" in content  # PII を含むスクリーンショット
    assert "output/" in content  # GLB / 入力画像
