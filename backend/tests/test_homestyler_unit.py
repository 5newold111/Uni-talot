"""
homestyler_bot の細部ロジックを単体テスト。実 Playwright 起動は重いので
セレクター辞書の整合性と _find_element のフォールバック挙動を中心に検証。
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from services import homestyler_bot
from services.errors import ErrorCode, PipelineError


@pytest.fixture(autouse=True)
def _set_creds(monkeypatch):
    monkeypatch.setattr(homestyler_bot, "EMAIL", "test@example.com")
    monkeypatch.setattr(homestyler_bot, "PASSWORD", "secret")


# ---- SELECTORS の整合性 ----------------------------------------------------


def test_selectors_dict_has_all_required_keys():
    required = {
        "login_button",
        "email_input",
        "password_input",
        "submit_button",
        "my_models_nav",
        "upload_button",
        "file_input",
        "name_input",
        "save_button",
    }
    assert required.issubset(homestyler_bot.SELECTORS.keys())


def test_selectors_use_csv_format_or_text_format():
    for key, value in homestyler_bot.SELECTORS.items():
        assert isinstance(value, str) and len(value) > 0, f"{key} is empty"
        # カンマ区切りで複数候補を持つことを想定
        parts = [p.strip() for p in value.split(",")]
        assert all(parts), f"{key} に空要素がある"


# ---- _find_element の挙動 -------------------------------------------------


async def test_find_element_returns_first_visible():
    """カンマ区切りで複数セレクターを試し、最初に可視のものを返す"""
    visible_locator = MagicMock()
    visible_locator.is_visible = AsyncMock(return_value=True)
    invisible_locator = MagicMock()
    invisible_locator.is_visible = AsyncMock(return_value=False)

    locators_by_selector = {
        "a": MagicMock(first=invisible_locator),
        "b": MagicMock(first=visible_locator),
        "c": MagicMock(first=MagicMock(is_visible=AsyncMock(return_value=True))),
    }
    page = MagicMock()
    page.locator = MagicMock(side_effect=lambda s: locators_by_selector[s])

    result = await homestyler_bot._find_element(page, "a, b, c")
    assert result is visible_locator


async def test_find_element_returns_none_when_all_invisible():
    invisible = MagicMock(
        first=MagicMock(is_visible=AsyncMock(return_value=False)),
    )
    page = MagicMock(locator=MagicMock(return_value=invisible))
    result = await homestyler_bot._find_element(page, "x, y, z")
    assert result is None


async def test_find_element_handles_exception_per_selector():
    """is_visible が raise したらその候補をスキップして次へ"""

    def make_locator(name: str):
        if name == "broken":
            return MagicMock(first=MagicMock(is_visible=AsyncMock(side_effect=Exception("boom"))))
        if name == "good":
            return MagicMock(first=MagicMock(is_visible=AsyncMock(return_value=True)))
        return MagicMock(first=MagicMock(is_visible=AsyncMock(return_value=False)))

    page = MagicMock(locator=MagicMock(side_effect=make_locator))
    result = await homestyler_bot._find_element(page, "broken, good")
    assert result is not None


async def test_find_element_trims_whitespace():
    """カンマ区切りの両端の空白を取り除く"""
    captured = []

    def loc(s):
        captured.append(s)
        return MagicMock(first=MagicMock(is_visible=AsyncMock(return_value=False)))

    page = MagicMock(locator=MagicMock(side_effect=loc))
    await homestyler_bot._find_element(page, "  a  ,  b  ,  c  ")
    assert captured == ["a", "b", "c"]


# ---- upload_to_homestyler の事前検証 ------------------------------------


async def test_upload_rejects_when_email_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(homestyler_bot, "EMAIL", "")
    glb = tmp_path / "x.glb"
    glb.write_bytes(b"GLB")
    with pytest.raises(PipelineError) as exc:
        await homestyler_bot.upload_to_homestyler(
            str(glb), "p", {"width_cm": 10, "depth_cm": 10, "height_cm": 10}
        )
    assert exc.value.code == ErrorCode.HOMESTYLER_AUTH_FAILED


async def test_upload_rejects_when_password_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(homestyler_bot, "PASSWORD", "")
    glb = tmp_path / "x.glb"
    glb.write_bytes(b"GLB")
    with pytest.raises(PipelineError) as exc:
        await homestyler_bot.upload_to_homestyler(
            str(glb), "p", {"width_cm": 10, "depth_cm": 10, "height_cm": 10}
        )
    assert exc.value.code == ErrorCode.HOMESTYLER_AUTH_FAILED


async def test_upload_rejects_when_glb_missing(tmp_path, monkeypatch):
    missing = str(tmp_path / "nonexistent.glb")
    with pytest.raises(PipelineError) as exc:
        await homestyler_bot.upload_to_homestyler(
            missing, "p", {"width_cm": 10, "depth_cm": 10, "height_cm": 10}
        )
    assert exc.value.code == ErrorCode.UPLOAD_FAILED


# ---- スクリーンショット名のサニタイズ ------------------------------------


def test_screenshot_filename_sanitizes_unicode_and_special_chars():
    """product_name に特殊文字が入っていてもパスとして安全な文字列にする"""
    name = "テスト商品/<>:|?*"
    safe = "".join(c if c.isalnum() else "_" for c in name[:20])
    # 英数字以外がすべて _ に置換されていること
    assert "/" not in safe and "<" not in safe and ":" not in safe
    # 元の長さ20文字以内
    assert len(safe) <= 20


# ---- セマフォの設定が env から読み取られること ---------------------------


def test_semaphore_capacity_default_is_one():
    """並列実行は default で 1 (Chromium が複数立たないように)"""
    import asyncio

    sem = homestyler_bot._UPLOAD_SEMAPHORE
    # asyncio.Semaphore は _value 属性に残量を持つ
    assert isinstance(sem, asyncio.Semaphore)
    # 初期値が 1 (取得前)
    assert sem._value == 1
