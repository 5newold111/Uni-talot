"""
v2.0 で追加された Homestyler キャリブレーション機構のテスト:
  - homestyler_storage_state.json の検出と context.storage_state パラメータ注入
  - homestyler_selectors.json による DEFAULT_SELECTORS 上書き
  - 失敗時の DOM/PNG/URL ダンプ
"""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from services import homestyler_bot


@pytest.fixture
def with_storage_state(tmp_path, monkeypatch):
    """`homestyler_storage_state.json` を一時的に存在させる"""
    p = tmp_path / "session.json"
    p.write_text(json.dumps({"cookies": [], "origins": []}))
    monkeypatch.setattr(homestyler_bot, "STORAGE_STATE_PATH", str(p))
    return p


@pytest.fixture
def with_selector_overrides(tmp_path, monkeypatch):
    """`homestyler_selectors.json` で SELECTORS を上書きする"""
    p = tmp_path / "selectors.json"
    overrides = {"upload_button": "button[data-test='upload']", "save_button": "#save-cta"}
    p.write_text(json.dumps(overrides))
    monkeypatch.setattr(homestyler_bot, "SELECTORS_OVERRIDE_PATH", str(p))
    return overrides


# ---- _load_selectors -------------------------------------------------------


def test_load_selectors_uses_defaults_when_no_override(tmp_path, monkeypatch):
    monkeypatch.setattr(homestyler_bot, "SELECTORS_OVERRIDE_PATH", str(tmp_path / "nope.json"))
    sel = homestyler_bot._load_selectors()
    assert sel == homestyler_bot.DEFAULT_SELECTORS


def test_load_selectors_applies_overrides(with_selector_overrides):
    sel = homestyler_bot._load_selectors()
    assert sel["upload_button"] == "button[data-test='upload']"
    assert sel["save_button"] == "#save-cta"
    # 上書きされていないキーは既定値のまま
    assert sel["email_input"] == homestyler_bot.DEFAULT_SELECTORS["email_input"]


def test_load_selectors_ignores_invalid_json(tmp_path, monkeypatch, caplog):
    p = tmp_path / "bad.json"
    p.write_text("not-json-at-all{{{")
    monkeypatch.setattr(homestyler_bot, "SELECTORS_OVERRIDE_PATH", str(p))
    sel = homestyler_bot._load_selectors()
    # 既定値にフォールバック
    assert sel == homestyler_bot.DEFAULT_SELECTORS


# ---- _have_storage_state --------------------------------------------------


def test_have_storage_state_false_when_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(homestyler_bot, "STORAGE_STATE_PATH", str(tmp_path / "missing.json"))
    assert homestyler_bot._have_storage_state() is False


def test_have_storage_state_false_when_empty(tmp_path, monkeypatch):
    p = tmp_path / "empty.json"
    p.write_bytes(b"")
    monkeypatch.setattr(homestyler_bot, "STORAGE_STATE_PATH", str(p))
    assert homestyler_bot._have_storage_state() is False


def test_have_storage_state_true_when_present(with_storage_state):
    assert homestyler_bot._have_storage_state() is True


# ---- upload_to_homestyler が storage_state を context に渡す -------------


async def test_upload_uses_storage_state_when_present(tmp_path, monkeypatch, with_storage_state):
    """セッションファイルがある場合: context が storage_state パラメータを受け取り、
    login ではなく直接 my_models ページに遷移する。"""

    glb = tmp_path / "test.glb"
    glb.write_bytes(b"GLB-binary")

    new_context_called = {}

    async def fake_new_context(**kwargs):
        new_context_called["kwargs"] = kwargs
        page = MagicMock()
        page.url = "https://www.homestyler.com/my-3d-models"
        page.goto = AsyncMock()
        page.wait_for_load_state = AsyncMock()
        page.wait_for_timeout = AsyncMock()
        page.screenshot = AsyncMock()
        page.content = AsyncMock(return_value="<html/>")
        page.locator = MagicMock(
            return_value=MagicMock(
                first=MagicMock(
                    is_visible=AsyncMock(return_value=False),
                    set_input_files=AsyncMock(),
                    wait_for=AsyncMock(),
                )
            )
        )
        ctx = MagicMock(
            new_page=AsyncMock(return_value=page),
        )
        return ctx

    browser = MagicMock(
        new_context=AsyncMock(side_effect=fake_new_context),
        close=AsyncMock(),
    )

    async def fake_launch(**kwargs):
        return browser

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=MagicMock(chromium=MagicMock(launch=fake_launch)))
    cm.__aexit__ = AsyncMock(return_value=None)

    def _async_locator():
        loc = MagicMock()
        loc.click = AsyncMock()
        loc.fill = AsyncMock()
        return loc

    async def fake_find_element_returns_button(page, sel):
        return _async_locator()

    monkeypatch.setattr(homestyler_bot, "async_playwright", lambda: cm)
    monkeypatch.setattr(homestyler_bot, "_find_element", fake_find_element_returns_button)

    await homestyler_bot.upload_to_homestyler(
        glb_path=str(glb),
        product_name="セッション復元テスト",
        dimensions={"width_cm": 100, "depth_cm": 50, "height_cm": 75},
    )

    # context が storage_state パラメータを受け取った
    assert "storage_state" in new_context_called["kwargs"]
    assert new_context_called["kwargs"]["storage_state"] == str(with_storage_state)


async def test_upload_skips_storage_state_when_absent(tmp_path, monkeypatch):
    """セッションファイルがない場合: storage_state パラメータが渡らない"""
    monkeypatch.setattr(homestyler_bot, "STORAGE_STATE_PATH", str(tmp_path / "no_session.json"))
    monkeypatch.setattr(homestyler_bot, "EMAIL", "x@example.com")
    monkeypatch.setattr(homestyler_bot, "PASSWORD", "pw")

    glb = tmp_path / "test.glb"
    glb.write_bytes(b"GLB")

    captured_kwargs = {}

    async def fake_new_context(**kwargs):
        captured_kwargs.update(kwargs)
        page = MagicMock()
        page.url = "https://www.homestyler.com/my-3d-models"
        for m in ("goto", "wait_for_load_state", "wait_for_timeout", "screenshot"):
            setattr(page, m, AsyncMock())
        page.keyboard = MagicMock(press=AsyncMock())
        page.content = AsyncMock(return_value="<html/>")
        page.locator = MagicMock(
            return_value=MagicMock(
                first=MagicMock(
                    is_visible=AsyncMock(return_value=False),
                    set_input_files=AsyncMock(),
                )
            )
        )
        return MagicMock(new_page=AsyncMock(return_value=page))

    async def fake_launch(**kwargs):
        return MagicMock(
            new_context=AsyncMock(side_effect=fake_new_context),
            close=AsyncMock(),
        )

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=MagicMock(chromium=MagicMock(launch=fake_launch)))
    cm.__aexit__ = AsyncMock(return_value=None)

    async def fake_find_anything(page, sel):
        return MagicMock(click=AsyncMock(), fill=AsyncMock())

    monkeypatch.setattr(homestyler_bot, "async_playwright", lambda: cm)
    monkeypatch.setattr(homestyler_bot, "_find_element", fake_find_anything)

    await homestyler_bot.upload_to_homestyler(
        glb_path=str(glb),
        product_name="ログインテスト",
        dimensions={"width_cm": 10, "depth_cm": 10, "height_cm": 10},
    )

    assert "storage_state" not in captured_kwargs


# ---- セレクター上書きが実際に upload で使われる ----------------------------


async def test_selector_overrides_used_in_upload(
    tmp_path, monkeypatch, with_selector_overrides, with_storage_state
):
    """上書きされた upload_button のセレクターが実際に _find_element に渡される"""

    glb = tmp_path / "t.glb"
    glb.write_bytes(b"GLB")

    seen_selectors = []

    async def fake_find_element(page, selector_string):
        seen_selectors.append(selector_string)
        return MagicMock(click=AsyncMock(), fill=AsyncMock())

    async def fake_new_context(**kwargs):
        page = MagicMock()
        page.url = "https://www.homestyler.com/my-3d-models"
        for m in ("goto", "wait_for_load_state", "wait_for_timeout", "screenshot"):
            setattr(page, m, AsyncMock())
        page.content = AsyncMock(return_value="<html/>")
        page.locator = MagicMock(
            return_value=MagicMock(
                first=MagicMock(
                    is_visible=AsyncMock(return_value=False),
                    set_input_files=AsyncMock(),
                )
            )
        )
        return MagicMock(new_page=AsyncMock(return_value=page))

    async def fake_launch(**kwargs):
        return MagicMock(
            new_context=AsyncMock(side_effect=fake_new_context),
            close=AsyncMock(),
        )

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=MagicMock(chromium=MagicMock(launch=fake_launch)))
    cm.__aexit__ = AsyncMock(return_value=None)
    monkeypatch.setattr(homestyler_bot, "async_playwright", lambda: cm)
    monkeypatch.setattr(homestyler_bot, "_find_element", fake_find_element)

    await homestyler_bot.upload_to_homestyler(
        glb_path=str(glb),
        product_name="セレクター上書きテスト",
        dimensions={"width_cm": 1, "depth_cm": 1, "height_cm": 1},
    )

    # 上書きしたセレクター文字列が _find_element に渡されている
    assert any("data-test='upload'" in s for s in seen_selectors)
    assert any("#save-cta" in s for s in seen_selectors)


# ---- 失効セッションの検出 ------------------------------------------------


async def test_expired_session_detected(tmp_path, monkeypatch, with_storage_state):
    """storage_state でアクセスしたら login ページにリダイレクトされた場合は
    HOMESTYLER_AUTH_FAILED で失敗する"""
    glb = tmp_path / "t.glb"
    glb.write_bytes(b"GLB")

    async def fake_new_context(**kwargs):
        page = MagicMock()
        page.url = "https://www.homestyler.com/signin?next=/my-3d-models"  # 失効リダイレクト
        for m in ("goto", "wait_for_load_state", "wait_for_timeout", "screenshot"):
            setattr(page, m, AsyncMock())
        page.content = AsyncMock(return_value="<html/>")
        page.locator = MagicMock(
            return_value=MagicMock(
                first=MagicMock(
                    is_visible=AsyncMock(return_value=False),
                )
            )
        )
        return MagicMock(new_page=AsyncMock(return_value=page))

    async def fake_launch(**kwargs):
        return MagicMock(new_context=AsyncMock(side_effect=fake_new_context), close=AsyncMock())

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=MagicMock(chromium=MagicMock(launch=fake_launch)))
    cm.__aexit__ = AsyncMock(return_value=None)
    monkeypatch.setattr(homestyler_bot, "async_playwright", lambda: cm)

    from services.errors import ErrorCode, PipelineError

    with pytest.raises(PipelineError) as exc:
        await homestyler_bot.upload_to_homestyler(
            glb_path=str(glb),
            product_name="失効検出",
            dimensions={"width_cm": 1, "depth_cm": 1, "height_cm": 1},
        )
    assert exc.value.code == ErrorCode.HOMESTYLER_AUTH_FAILED
    assert "失効" in exc.value.message


# ---- 失敗時の DOM ダンプ ------------------------------------------------


async def test_debug_dump_on_failure(tmp_path, monkeypatch):
    """upload_button が見つからない場合、HTML/PNG が logs/ に出力される"""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(homestyler_bot, "STORAGE_STATE_PATH", str(tmp_path / "no_session.json"))
    monkeypatch.setattr(homestyler_bot, "EMAIL", "x@example.com")
    monkeypatch.setattr(homestyler_bot, "PASSWORD", "p")

    glb = tmp_path / "g.glb"
    glb.write_bytes(b"GLB")

    screenshot_calls = []
    content_calls = []

    async def fake_screenshot(path=None, **kwargs):
        screenshot_calls.append(path)
        # 実ファイルも書き出して存在確認できるようにする
        if path:
            from pathlib import Path

            Path(path).write_bytes(b"PNG-stub")

    async def fake_content():
        content_calls.append(1)
        return "<html><body>page dump</body></html>"

    async def fake_new_context(**kwargs):
        page = MagicMock()
        page.url = "https://www.homestyler.com/something"
        page.goto = AsyncMock()
        page.wait_for_load_state = AsyncMock()
        page.wait_for_timeout = AsyncMock()
        page.keyboard = MagicMock(press=AsyncMock())
        page.screenshot = fake_screenshot
        page.content = fake_content
        page.locator = MagicMock(
            return_value=MagicMock(
                first=MagicMock(
                    is_visible=AsyncMock(return_value=False),
                    set_input_files=AsyncMock(),
                )
            )
        )
        return MagicMock(new_page=AsyncMock(return_value=page))

    async def fake_launch(**kwargs):
        return MagicMock(new_context=AsyncMock(side_effect=fake_new_context), close=AsyncMock())

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=MagicMock(chromium=MagicMock(launch=fake_launch)))
    cm.__aexit__ = AsyncMock(return_value=None)
    monkeypatch.setattr(homestyler_bot, "async_playwright", lambda: cm)

    # email_input は見つけて login は通過するが、upload_button で None を返す
    call_count = [0]

    async def fake_find(page, sel):
        call_count[0] += 1
        # ログイン関係 (email/password/submit) は通す
        if any(k in sel.lower() for k in ["email", "password", "sign in", "submit", "nav"]):
            return MagicMock(click=AsyncMock(), fill=AsyncMock())
        # upload_button で None → UI_CHANGED エラー
        return None

    monkeypatch.setattr(homestyler_bot, "_find_element", fake_find)

    from services.errors import ErrorCode, PipelineError

    with pytest.raises(PipelineError) as exc:
        await homestyler_bot.upload_to_homestyler(
            glb_path=str(glb),
            product_name="ダンプテスト",
            dimensions={"width_cm": 1, "depth_cm": 1, "height_cm": 1},
        )
    assert exc.value.code in (ErrorCode.HOMESTYLER_UI_CHANGED, ErrorCode.UPLOAD_FAILED)
    # スクリーンショット保存と HTML 取得が呼ばれている
    assert len(screenshot_calls) >= 1
    assert len(content_calls) >= 1
    # logs/ にダンプファイルが残っている
    logs = list((tmp_path / "logs").glob("error_*"))
    assert len(logs) >= 2  # png + html (+ url.txt)
