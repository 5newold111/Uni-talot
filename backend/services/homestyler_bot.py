import asyncio
import logging
import os

from dotenv import load_dotenv
from playwright.async_api import TimeoutError as PlaywrightTimeout
from playwright.async_api import async_playwright

from services.errors import ErrorCode, PipelineError

load_dotenv()
logger = logging.getLogger(__name__)

EMAIL = os.getenv("HOMESTYLER_EMAIL", "")
PASSWORD = os.getenv("HOMESTYLER_PASSWORD", "")

# 各呼び出しが Chromium プロセスを起動するため、並列実行するとメモリと
# Homestyler 側のレート制限の両方で問題が起こる。Semaphore で直列化する。
_UPLOAD_SEMAPHORE = asyncio.Semaphore(int(os.getenv("HOMESTYLER_MAX_CONCURRENCY", "1")))

SELECTORS = {
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


async def upload_to_homestyler(
    glb_path: str, product_name: str, dimensions: dict, category: str = "家具"
):
    """
    Playwright を使って Homestyler に GLB をアップロードする。
    headless=False にすると操作をリアルタイムで目視確認できる（デバッグ時に推奨）。
    """
    if not EMAIL or not PASSWORD:
        raise PipelineError(
            ErrorCode.HOMESTYLER_AUTH_FAILED,
            "HOMESTYLER_EMAIL または HOMESTYLER_PASSWORD が設定されていません",
        )

    glb_abs_path = os.path.abspath(glb_path)
    if not os.path.exists(glb_abs_path):
        raise PipelineError(
            ErrorCode.UPLOAD_FAILED,
            f"アップロードするGLBファイルが存在しません: {glb_abs_path}",
        )

    os.makedirs("logs", exist_ok=True)

    async with _UPLOAD_SEMAPHORE, async_playwright() as p:
        browser = await p.chromium.launch(headless=True, slow_mo=500)
        context = await browser.new_context(viewport={"width": 1280, "height": 800})
        page = await context.new_page()

        try:
            logger.info("Homestyler にアクセスしています...")
            await page.goto("https://www.homestyler.com/", timeout=30000)
            await page.wait_for_load_state("networkidle", timeout=15000)

            login_btn = await _find_element(page, SELECTORS["login_button"])
            if login_btn:
                await login_btn.click()
                await page.wait_for_timeout(1500)

            email_field = await _find_element(page, SELECTORS["email_input"])
            if not email_field:
                raise PipelineError(
                    ErrorCode.HOMESTYLER_UI_CHANGED,
                    "メール入力フィールドが見つかりません。セレクターを確認してください",
                )
            await email_field.fill(EMAIL)

            password_field = await _find_element(page, SELECTORS["password_input"])
            if not password_field:
                raise PipelineError(
                    ErrorCode.HOMESTYLER_UI_CHANGED, "パスワード入力フィールドが見つかりません"
                )
            await password_field.fill(PASSWORD)

            submit = await _find_element(page, SELECTORS["submit_button"])
            if submit:
                await submit.click()
            else:
                await page.keyboard.press("Enter")

            await page.wait_for_load_state("networkidle", timeout=20000)
            logger.info("ログイン完了")

            await page.wait_for_timeout(2000)
            nav = await _find_element(page, SELECTORS["my_models_nav"])
            if nav:
                await nav.click()
            else:
                await page.goto("https://www.homestyler.com/my-3d-models", timeout=20000)

            await page.wait_for_load_state("networkidle", timeout=15000)
            logger.info("マイモデルページに移動しました")

            upload_btn = await _find_element(page, SELECTORS["upload_button"])
            if not upload_btn:
                raise PipelineError(
                    ErrorCode.HOMESTYLER_UI_CHANGED, "アップロードボタンが見つかりません"
                )
            await upload_btn.click()
            await page.wait_for_timeout(2000)

            file_input = page.locator("input[type='file']").first
            await file_input.set_input_files(glb_abs_path)
            logger.info(f"GLBファイルを選択: {glb_abs_path}")
            await page.wait_for_timeout(3000)

            name_field = await _find_element(page, SELECTORS["name_input"])
            if name_field:
                await name_field.fill(product_name)

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

            save_btn = await _find_element(page, SELECTORS["save_button"])
            if save_btn:
                await save_btn.click()

            await page.wait_for_timeout(3000)
            logger.info(f"Homestylerへのアップロード完了: {product_name}")

        except PipelineError:
            # 構造化エラーはそのまま伝播
            safe_name = "".join(c if c.isalnum() else "_" for c in product_name[:20])
            try:
                await page.screenshot(path=f"logs/error_{safe_name}.png")
            except Exception:
                pass
            raise
        except Exception as e:
            safe_name = "".join(c if c.isalnum() else "_" for c in product_name[:20])
            screenshot_path = f"logs/error_{safe_name}.png"
            try:
                await page.screenshot(path=screenshot_path)
                logger.error(f"エラー発生。スクリーンショット保存: {screenshot_path}")
            except Exception:
                logger.error("スクリーンショットの保存にも失敗しました")
            raise PipelineError(
                ErrorCode.UPLOAD_FAILED, f"Homestyler操作エラー: {str(e)}", original=e
            ) from e

        finally:
            await browser.close()


async def _find_element(page, selector_string: str):
    """
    カンマ区切りのセレクター文字列を順番に試し、最初に見つかった要素を返す。
    すべて見つからない場合は None を返す。
    """
    for selector in [s.strip() for s in selector_string.split(",")]:
        try:
            element = page.locator(selector).first
            if await element.is_visible(timeout=3000):
                return element
        except Exception:
            continue
    return None
