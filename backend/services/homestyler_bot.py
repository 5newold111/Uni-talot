"""
Homestyler への GLB アップロードを Playwright で自動化する。

v2.0 でコアパイプラインから分離されたオプショナル後処理。
Homestyler には公式 API がないため、ブラウザ自動操作で対応する。

## 認証方式

1. **storage_state (推奨)**: 事前に `python scripts/calibrate_homestyler.py login` で
   ブラウザを立ち上げ、ユーザーが手動でログイン → セッション Cookie を
   `homestyler_storage_state.json` に保存。以後はそれを使うので CAPTCHA や
   OAuth (Google login) を毎回突破する必要がない。
2. **email/password (フォールバック)**: `HOMESTYLER_EMAIL` / `HOMESTYLER_PASSWORD`
   から自動ログインを試みる。CAPTCHA があると詰む。

## セレクター上書き

`homestyler_selectors.json` が存在すれば、その内容で `SELECTORS` を上書きする。
コードを変更せず、calibrate ツールから実画面で取得したセレクターに差し替え可能。

## 失敗時のデバッグ

`UPLOAD_FAILED` 系のエラーが起きると `logs/error_<product>_<ts>.html` に
ページ DOM、`logs/error_<product>_<ts>.png` にスクリーンショットが保存される。
"""

import asyncio
import json
import logging
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from playwright.async_api import TimeoutError as PlaywrightTimeout
from playwright.async_api import async_playwright

from services.errors import ErrorCode, PipelineError

load_dotenv()
logger = logging.getLogger(__name__)

EMAIL = os.getenv("HOMESTYLER_EMAIL", "")
PASSWORD = os.getenv("HOMESTYLER_PASSWORD", "")

# 各呼び出しが Chromium プロセスを起動するため、Semaphore で直列化する。
_UPLOAD_SEMAPHORE = asyncio.Semaphore(int(os.getenv("HOMESTYLER_MAX_CONCURRENCY", "1")))

# 保存済みセッション / セレクター上書きファイルのパス
STORAGE_STATE_PATH = os.getenv("HOMESTYLER_STORAGE_STATE", "homestyler_storage_state.json")
SELECTORS_OVERRIDE_PATH = os.getenv("HOMESTYLER_SELECTORS", "homestyler_selectors.json")

# Homestyler の各画面 URL (実画面で変わったら calibrate で上書き)
URLS = {
    "home": "https://www.homestyler.com/",
    "my_models": "https://www.homestyler.com/my-3d-models",
}

# 既定セレクター。実画面で動かない場合は `homestyler_selectors.json` で上書き。
DEFAULT_SELECTORS = {
    "login_button": "text=Log in",
    "email_input": "input[type='email'], input[name='email'], #email",
    "password_input": "input[type='password'], input[name='password'], #password",
    "submit_button": "button[type='submit'], .login-btn, text=Sign in",
    "my_models_nav": "text=My 3D Models, text=マイモデル, [href*='my-3d-model']",
    "upload_button": "text=Upload, text=アップロード, .upload-btn",
    "file_input": "input[type='file']",
    "name_input": "input[name='name'], input[placeholder*='name'], input[placeholder*='名前']",
    "save_button": "text=Save, text=保存, button[type='submit']",
}


def _load_selectors() -> dict:
    """`homestyler_selectors.json` で上書きされたセレクターを優先する。"""
    overrides: dict = {}
    p = Path(SELECTORS_OVERRIDE_PATH)
    if p.is_file():
        try:
            overrides = json.loads(p.read_text(encoding="utf-8"))
            logger.info(
                f"セレクター上書きを読み込み: {SELECTORS_OVERRIDE_PATH} ({len(overrides)} keys)"
            )
        except Exception as e:
            logger.warning(f"{SELECTORS_OVERRIDE_PATH} 解析失敗: {e}, 既定セレクターを使う")
    return {**DEFAULT_SELECTORS, **overrides}


# 後方互換: 外部からは `SELECTORS` で参照できるよう保持
SELECTORS = _load_selectors()


def _have_storage_state() -> bool:
    p = Path(STORAGE_STATE_PATH)
    return p.is_file() and p.stat().st_size > 0


async def _save_debug_dump(page, product_name: str, reason: str) -> None:
    """失敗時に HTML / PNG / 現在 URL を保存する。後でセレクター修正に活用。"""
    os.makedirs("logs", exist_ok=True)
    ts = int(time.time())
    safe = "".join(c if c.isalnum() else "_" for c in product_name[:20]) or "anon"
    base = f"logs/error_{safe}_{ts}"
    try:
        await page.screenshot(path=f"{base}.png", full_page=True)
    except Exception:
        pass
    try:
        html = await page.content()
        Path(f"{base}.html").write_text(html, encoding="utf-8")
    except Exception:
        pass
    try:
        cur_url = page.url
        Path(f"{base}.url.txt").write_text(cur_url, encoding="utf-8")
    except Exception:
        pass
    logger.error(f"デバッグダンプ保存: {base}.{{png,html,url.txt}} ({reason})")


async def _login_with_credentials(page, selectors: dict) -> None:
    """email/password で自動ログイン。CAPTCHA/OAuth があるとここで詰む。"""
    if not EMAIL or not PASSWORD:
        raise PipelineError(
            ErrorCode.HOMESTYLER_AUTH_FAILED,
            "HOMESTYLER_EMAIL/PASSWORD が未設定。calibrate でログインセッションを作るか .env を設定",
        )
    logger.info("Homestyler にアクセスしています...")
    await page.goto(URLS["home"], timeout=30000)
    await page.wait_for_load_state("networkidle", timeout=15000)

    login_btn = await _find_element(page, selectors["login_button"])
    if login_btn:
        await login_btn.click()
        await page.wait_for_timeout(1500)

    email_field = await _find_element(page, selectors["email_input"])
    if not email_field:
        raise PipelineError(
            ErrorCode.HOMESTYLER_UI_CHANGED,
            "メール入力フィールドが見つかりません。calibrate ツールでセレクター更新を",
        )
    await email_field.fill(EMAIL)

    password_field = await _find_element(page, selectors["password_input"])
    if not password_field:
        raise PipelineError(
            ErrorCode.HOMESTYLER_UI_CHANGED, "パスワード入力フィールドが見つかりません"
        )
    await password_field.fill(PASSWORD)

    submit = await _find_element(page, selectors["submit_button"])
    if submit:
        await submit.click()
    else:
        await page.keyboard.press("Enter")

    await page.wait_for_load_state("networkidle", timeout=20000)
    logger.info("自動ログイン完了 (email/password)")


async def upload_to_homestyler(
    glb_path: str, product_name: str, dimensions: dict, category: str = "家具"
):
    """
    Playwright で Homestyler に GLB をアップロードする。

    認証は以下の順で試みる:
      1. `homestyler_storage_state.json` があればセッション復元 (推奨)
      2. なければ email/password で自動ログイン
    """
    glb_abs_path = os.path.abspath(glb_path)
    if not os.path.exists(glb_abs_path):
        raise PipelineError(
            ErrorCode.UPLOAD_FAILED,
            f"アップロードする GLB ファイルが存在しません: {glb_abs_path}",
        )

    # 早期認証チェック: storage_state も email/password も無ければ Playwright を
    # 起動する前に失敗させる (Chromium 起動は重いので意味のある検査を先に)
    if not _have_storage_state() and (not EMAIL or not PASSWORD):
        raise PipelineError(
            ErrorCode.HOMESTYLER_AUTH_FAILED,
            f"認証情報がありません: {STORAGE_STATE_PATH} もなく、"
            "HOMESTYLER_EMAIL/PASSWORD も未設定です。"
            "`python scripts/calibrate_homestyler.py login` でセッションを作るか、"
            ".env に認証情報を設定してください",
        )

    selectors = _load_selectors()
    os.makedirs("logs", exist_ok=True)
    headless = os.getenv("HOMESTYLER_HEADLESS", "true").lower() != "false"

    async with _UPLOAD_SEMAPHORE, async_playwright() as p:
        browser = await p.chromium.launch(
            headless=headless, slow_mo=int(os.getenv("HOMESTYLER_SLOW_MO", "300"))
        )

        # storage_state が保存済みならセッション復元、なければ素の context
        ctx_kwargs = {"viewport": {"width": 1280, "height": 800}}
        if _have_storage_state():
            ctx_kwargs["storage_state"] = STORAGE_STATE_PATH
            logger.info(f"セッション復元: {STORAGE_STATE_PATH}")

        context = await browser.new_context(**ctx_kwargs)
        page = await context.new_page()

        try:
            if _have_storage_state():
                # 既にログイン済みなのでマイモデルに直行
                await page.goto(URLS["my_models"], timeout=30000)
                await page.wait_for_load_state("networkidle", timeout=15000)
                # セッションが切れていれば再認証画面に飛ぶので検出する
                if "login" in page.url.lower() or "signin" in page.url.lower():
                    raise PipelineError(
                        ErrorCode.HOMESTYLER_AUTH_FAILED,
                        f"保存セッションが失効しています。calibrate で再ログインしてください: {page.url}",
                    )
            else:
                await _login_with_credentials(page, selectors)
                # ログイン後にマイモデルへ移動
                nav = await _find_element(page, selectors["my_models_nav"])
                if nav:
                    await nav.click()
                else:
                    await page.goto(URLS["my_models"], timeout=20000)
                await page.wait_for_load_state("networkidle", timeout=15000)

            logger.info(f"マイモデル画面: {page.url}")

            # アップロードボタン
            upload_btn = await _find_element(page, selectors["upload_button"])
            if not upload_btn:
                raise PipelineError(
                    ErrorCode.HOMESTYLER_UI_CHANGED, "アップロードボタンが見つかりません"
                )
            await upload_btn.click()
            await page.wait_for_timeout(2000)

            # ファイル input
            file_input = page.locator(selectors["file_input"]).first
            await file_input.set_input_files(glb_abs_path)
            logger.info(f"GLB ファイルを選択: {glb_abs_path}")
            await page.wait_for_timeout(3000)

            # 商品名
            name_field = await _find_element(page, selectors["name_input"])
            if name_field:
                await name_field.fill(product_name)

            # 寸法 (フィールドが存在すれば)
            for field_name, cm_value in [
                ("width", dimensions.get("width_cm", 0)),
                ("depth", dimensions.get("depth_cm", 0)),
                ("height", dimensions.get("height_cm", 0)),
            ]:
                field = page.locator(
                    f"input[name='{field_name}'], input[placeholder*='{field_name}']"
                ).first
                try:
                    if await field.is_visible(timeout=2000):
                        await field.fill(str(cm_value))
                except PlaywrightTimeout:
                    pass

            # 保存
            save_btn = await _find_element(page, selectors["save_button"])
            if save_btn:
                await save_btn.click()

            await page.wait_for_timeout(3000)
            logger.info(f"Homestyler アップロード完了: {product_name}")

        except PipelineError:
            await _save_debug_dump(page, product_name, "pipeline_error")
            raise
        except Exception as e:
            await _save_debug_dump(page, product_name, f"unexpected: {e}")
            raise PipelineError(
                ErrorCode.UPLOAD_FAILED, f"Homestyler 操作エラー: {str(e)}", original=e
            ) from e
        finally:
            await browser.close()


async def _find_element(page, selector_string: str):
    """カンマ区切りで複数のセレクターを試し、最初に可視のものを返す。"""
    for selector in [s.strip() for s in selector_string.split(",")]:
        if not selector:
            continue
        try:
            element = page.locator(selector).first
            if await element.is_visible(timeout=3000):
                return element
        except Exception:
            continue
    return None
