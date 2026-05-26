"""
Homestyler bot のセマフォが並行実行を直列化することを検証する。
async_playwright をモックして、同時に何個 launch されているかを観測。
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services import homestyler_bot


@pytest.fixture(autouse=True)
def credentials(monkeypatch):
    monkeypatch.setattr(homestyler_bot, "EMAIL", "test@example.com")
    monkeypatch.setattr(homestyler_bot, "PASSWORD", "x")


async def test_uploads_run_serially_under_semaphore(tmp_path, monkeypatch):
    # GLB ファイルを用意
    glb = tmp_path / "x_scaled.glb"
    glb.write_bytes(b"GLB")

    concurrent = 0
    max_concurrent = 0
    lock = asyncio.Lock()

    @patch("services.homestyler_bot.async_playwright")
    async def run(mock_playwright):
        nonlocal concurrent, max_concurrent

        async def fake_launch(**kwargs):
            nonlocal concurrent, max_concurrent
            async with lock:
                concurrent += 1
                max_concurrent = max(max_concurrent, concurrent)
            # 実際の作業を模擬
            await asyncio.sleep(0.05)
            async with lock:
                concurrent -= 1

            # browser モック
            browser = MagicMock()
            context = MagicMock()
            page = MagicMock()
            page.goto = AsyncMock()
            page.wait_for_load_state = AsyncMock()
            page.wait_for_timeout = AsyncMock()
            page.keyboard.press = AsyncMock()
            page.locator = MagicMock(
                return_value=MagicMock(
                    set_input_files=AsyncMock(),
                    is_visible=AsyncMock(return_value=False),
                )
            )
            context.new_page = AsyncMock(return_value=page)
            browser.new_context = AsyncMock(return_value=context)
            browser.close = AsyncMock()
            return browser

        cm = MagicMock()
        cm.__aenter__ = AsyncMock(return_value=MagicMock(chromium=MagicMock(launch=fake_launch)))
        cm.__aexit__ = AsyncMock(return_value=None)
        mock_playwright.return_value = cm

        # _find_element は None を返してセレクター未発見扱い→ RuntimeError
        async def fake_find_element(page, sel):
            return None

        monkeypatch.setattr(homestyler_bot, "_find_element", fake_find_element)

        # 5並列で起動を試みる
        tasks = [
            homestyler_bot.upload_to_homestyler(
                glb_path=str(glb),
                product_name=f"p{i}",
                dimensions={"width_cm": 1, "depth_cm": 1, "height_cm": 1},
            )
            for i in range(5)
        ]
        # 全て失敗するが、それは想定内 (セマフォの動作だけを確認)
        await asyncio.gather(*tasks, return_exceptions=True)

    await run()

    # Semaphore(1) なので並行数は常に 1 を超えない
    assert max_concurrent == 1, f"max concurrent launches = {max_concurrent}, expected 1"
