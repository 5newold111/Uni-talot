#!/usr/bin/env python3
"""
Homestyler セレクター & セッションのキャリブレーション CLI。

サブコマンド:

    python scripts/calibrate_homestyler.py login
        Chromium を headless=False で起動 → ユーザーが手動でログイン
        (Google OAuth / CAPTCHA 含む) → Enter を押すと
        homestyler_storage_state.json にセッションを保存。
        以後の自動アップロードはこのセッションを使い、再ログイン不要。

    python scripts/calibrate_homestyler.py capture <selector_name>
        既存セッションでマイモデル画面を開き、ユーザーがブラウザでクリックした
        要素の CSS セレクターを推定して homestyler_selectors.json に保存。
        例: capture upload_button / capture save_button

    python scripts/calibrate_homestyler.py probe
        既存セッションで Homestyler を開き、現在の SELECTORS が各画面に
        存在するか可視性チェック。実画面の DOM 構造変更を素早く検出。

    python scripts/calibrate_homestyler.py dump-dom
        現在の DOM スナップショットを logs/calibration_<ts>.html に保存。
        セレクターを手動で探すときに使う。

実行前提:
    pip install playwright && python -m playwright install chromium
"""

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

# `backend/` をパスに追加して services をインポートできるようにする
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from playwright.async_api import async_playwright  # noqa: E402

from services import homestyler_bot  # noqa: E402

STORAGE = ROOT / "homestyler_storage_state.json"
SELECTORS_FILE = ROOT / "homestyler_selectors.json"


async def cmd_login(_args) -> int:
    print("=" * 60)
    print("Homestyler セッションキャリブレーション")
    print("=" * 60)
    print("1. ブラウザが立ち上がります")
    print("2. ホームページが開いたら手動でログインしてください")
    print("   - メール/パスワード または Google OAuth のいずれでも可")
    print("   - CAPTCHA / 2FA が出たら通常通り突破してください")
    print("3. マイモデル画面まで到達したらこのターミナルに戻って Enter を押してください")
    print("4. セッションが", STORAGE.name, "に保存されます")
    print()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(viewport={"width": 1280, "height": 800})
        page = await context.new_page()
        await page.goto(homestyler_bot.URLS["home"])

        # 別スレッドで input() を受けてからセッション保存
        print("→ ログイン完了後、このターミナルで Enter を押してください...", end="", flush=True)
        await asyncio.to_thread(input)

        await context.storage_state(path=str(STORAGE))
        print(f"\n✓ セッション保存: {STORAGE}")
        await browser.close()
    return 0


async def _open_with_session(p, headless=False):
    """保存済みセッションで context を作って開く。"""
    if not STORAGE.is_file():
        print(f"ERROR: {STORAGE} がありません。先に `calibrate login` を実行してください")
        return None, None, None
    browser = await p.chromium.launch(headless=headless)
    context = await browser.new_context(
        viewport={"width": 1280, "height": 800}, storage_state=str(STORAGE)
    )
    page = await context.new_page()
    return browser, context, page


async def cmd_capture(args) -> int:
    """ユーザーがブラウザでクリックした要素のセレクターを抽出して保存"""
    target_name = args.selector_name
    if target_name not in homestyler_bot.DEFAULT_SELECTORS:
        print(f"ERROR: 未知のセレクター名: {target_name}")
        print(f"有効: {list(homestyler_bot.DEFAULT_SELECTORS.keys())}")
        return 1

    print("=" * 60)
    print(f"セレクターキャプチャ: {target_name}")
    print("=" * 60)
    print("ブラウザでマイモデル画面に移動 → 該当要素を **右クリック → 検証**")
    print("ターミナルに戻り、DevTools で見えた CSS セレクターを入力してください")
    print()

    async with async_playwright() as p:
        browser, context, page = await _open_with_session(p, headless=False)
        if browser is None:
            return 1
        await page.goto(homestyler_bot.URLS["my_models"])
        print(f"→ 開いた画面: {page.url}")
        print("→ 該当要素のセレクターを入力して Enter (例: 'button.upload-btn'):")
        new_selector = (await asyncio.to_thread(input)).strip()
        if not new_selector:
            print("入力が空でした。中止")
            await browser.close()
            return 1

        # 入力したセレクターが実際に可視か検証
        try:
            await page.locator(new_selector).first.wait_for(state="visible", timeout=5000)
            print(f"✓ 入力されたセレクターは可視: {new_selector!r}")
        except Exception as e:
            print(f"⚠ セレクターが見つかりません: {e}")
            print("  (それでも保存しますか? y/N): ", end="", flush=True)
            ans = (await asyncio.to_thread(input)).strip().lower()
            if ans != "y":
                await browser.close()
                return 1

        # JSON ファイルに保存 (既存と merge)
        overrides = {}
        if SELECTORS_FILE.is_file():
            overrides = json.loads(SELECTORS_FILE.read_text(encoding="utf-8"))
        overrides[target_name] = new_selector
        SELECTORS_FILE.write_text(
            json.dumps(overrides, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"✓ 保存: {SELECTORS_FILE} ({len(overrides)} keys)")
        await browser.close()
    return 0


async def cmd_probe(_args) -> int:
    """既定セレクターが各画面で動くか可視性チェック"""
    print("=" * 60)
    print("セレクター可視性チェック")
    print("=" * 60)
    selectors = homestyler_bot._load_selectors()

    async with async_playwright() as p:
        browser, context, page = await _open_with_session(p, headless=True)
        if browser is None:
            return 1

        await page.goto(homestyler_bot.URLS["my_models"])
        await page.wait_for_load_state("networkidle", timeout=15000)

        results = {}
        for name, sel in selectors.items():
            found = await homestyler_bot._find_element(page, sel)
            results[name] = bool(found)
            mark = "✓" if found else "✗"
            print(f"  {mark} {name:<20} -> {sel[:60]}")

        await browser.close()

    ok_count = sum(1 for v in results.values() if v)
    total = len(results)
    print(f"\n{ok_count}/{total} セレクター可視")
    return 0 if ok_count == total else 1


async def cmd_dump_dom(_args) -> int:
    """現在画面の DOM とスクリーンショットを保存"""
    os.makedirs("logs", exist_ok=True)
    ts = int(time.time())
    out_html = ROOT / "logs" / f"calibration_{ts}.html"
    out_png = ROOT / "logs" / f"calibration_{ts}.png"
    out_url = ROOT / "logs" / f"calibration_{ts}.url.txt"

    async with async_playwright() as p:
        browser, context, page = await _open_with_session(p, headless=True)
        if browser is None:
            return 1
        await page.goto(homestyler_bot.URLS["my_models"])
        await page.wait_for_load_state("networkidle", timeout=15000)
        out_html.write_text(await page.content(), encoding="utf-8")
        await page.screenshot(path=str(out_png), full_page=True)
        out_url.write_text(page.url, encoding="utf-8")
        await browser.close()

    print(f"✓ DOM: {out_html}")
    print(f"✓ PNG: {out_png}")
    print(f"✓ URL: {out_url}")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        prog="calibrate_homestyler",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = p.add_subparsers(dest="command", required=True)

    s_login = sub.add_parser("login", help="ブラウザで手動ログイン → セッション保存")
    s_login.set_defaults(func=cmd_login)

    s_cap = sub.add_parser("capture", help="セレクターを 1 つ上書き保存")
    s_cap.add_argument("selector_name", help=f"対象: {list(homestyler_bot.DEFAULT_SELECTORS)}")
    s_cap.set_defaults(func=cmd_capture)

    s_probe = sub.add_parser("probe", help="既定セレクターの可視性チェック")
    s_probe.set_defaults(func=cmd_probe)

    s_dump = sub.add_parser("dump-dom", help="現在画面の HTML/PNG/URL を保存")
    s_dump.set_defaults(func=cmd_dump_dom)

    args = p.parse_args(argv)
    return asyncio.run(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
