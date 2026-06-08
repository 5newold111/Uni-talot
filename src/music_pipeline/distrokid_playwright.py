"""DistroKid アップロードのブラウザ自動操作版（opt-in / 上級者向け）。

⚠️ 重要な注意:
- DistroKid には公式アップロード API が無いため、これは自分のアカウントの
  操作を Playwright で自動化するものです。**自分のアカウントに対してのみ**使用し、
  DistroKid の利用規約を順守してください。規約変更や画面変更で容易に壊れます。
- 既定では **最終送信を行いません**（`auto_submit: false`）。全項目を入力後に
  スクリーンショットを保存して終了するので、人が内容を確認してから送信できます。
- CSS セレクタは画面変更で変わり得るため `config.yaml の distribution.playwright.selectors`
  で上書きできるようにしています（要・実環境での検証）。

依存:
    pip install playwright && playwright install chromium

認証情報（環境変数）:
    DISTROKID_EMAIL, DISTROKID_PASSWORD
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from .config import Settings
from .models import Album, Track

logger = logging.getLogger(__name__)

# 既定セレクタ（実環境で要検証 / config で上書き可能）
DEFAULT_SELECTORS = {
    "login_email": "input[type=email], #email",
    "login_password": "input[type=password], #password",
    "login_submit": "button[type=submit], #login-button",
    "logged_in_marker": "text=Upload",
    "upload_nav": "text=Upload",
    "artist_name": "#artist_name, input[name='artist']",
    "album_title": "#album_title, input[name='title']",
    "track_audio_input": "input[type=file][accept*='audio']",
    "cover_input": "input[type=file][accept*='image']",
    "submit": "#submit, button:has-text('Submit')",
}


class DistroKidPlaywrightUploader:
    def __init__(self, settings: Settings):
        self.settings = settings
        cfg = (settings.section("distribution").get("playwright") or {})
        self.base_url = cfg.get("base_url", "https://distrokid.com")
        self.headless = bool(cfg.get("headless", True))
        self.auto_submit = bool(cfg.get("auto_submit", False))
        self.timeout_ms = int(cfg.get("timeout_ms", 30000))
        self.selectors = {**DEFAULT_SELECTORS, **(cfg.get("selectors") or {})}
        self.email = os.getenv("DISTROKID_EMAIL", "")
        self.password = os.getenv("DISTROKID_PASSWORD", "")

    # --- public ---
    def upload(self, album: Album, tracks: list[Track], package_dir: Path) -> bool:
        """配信パッケージを DistroKid にアップロードする。

        返り値: 送信まで完了したら True、レビュー停止（auto_submit=False）なら False。
        """
        if not (self.email and self.password):
            raise RuntimeError(
                "DISTROKID_EMAIL / DISTROKID_PASSWORD が未設定です。自動アップロードできません。"
            )
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "playwright が未導入です。`pip install playwright && playwright install chromium`"
            ) from exc

        shots = package_dir / "playwright"
        shots.mkdir(parents=True, exist_ok=True)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            page = browser.new_page()
            page.set_default_timeout(self.timeout_ms)
            try:
                self._login(page, shots)
                self._open_upload(page, shots)
                self._fill_album(page, album, tracks, package_dir, shots)
                page.screenshot(path=str(shots / "before_submit.png"), full_page=True)

                if not self.auto_submit:
                    logger.warning(
                        "auto_submit=false のため送信せず終了。%s を確認して手動送信してください。",
                        shots / "before_submit.png",
                    )
                    return False

                self._submit(page, shots)
                page.screenshot(path=str(shots / "after_submit.png"), full_page=True)
                logger.info("DistroKid 送信完了。")
                return True
            except Exception:
                try:
                    page.screenshot(path=str(shots / "error.png"), full_page=True)
                except Exception:
                    pass
                raise
            finally:
                browser.close()

    # --- steps（実環境のセレクタに合わせて要調整）---
    def _login(self, page, shots: Path) -> None:
        page.goto(f"{self.base_url}/signin")
        page.fill(self.selectors["login_email"], self.email)
        page.fill(self.selectors["login_password"], self.password)
        page.click(self.selectors["login_submit"])
        # 2FA 等がある場合はここで手動対応が必要（headless=false 推奨）
        page.wait_for_selector(self.selectors["logged_in_marker"])
        logger.info("DistroKid ログイン成功")

    def _open_upload(self, page, shots: Path) -> None:
        page.click(self.selectors["upload_nav"])
        page.wait_for_load_state("networkidle")

    def _fill_album(self, page, album: Album, tracks: list[Track],
                    package_dir: Path, shots: Path) -> None:
        artist = self.settings.section("label").get("artist_name", "AI Sound Lab")
        self._safe_fill(page, self.selectors["artist_name"], artist)
        self._safe_fill(page, self.selectors["album_title"], album.title)

        # カバー（PNG/JPG が必要。SVG しか無い場合は警告）
        cover = Path(album.cover_path) if album.cover_path else None
        if cover and cover.exists() and cover.suffix.lower() in (".png", ".jpg", ".jpeg"):
            self._safe_set_files(page, self.selectors["cover_input"], cover)
        else:
            logger.warning("カバーが PNG/JPG ではありません（%s）。手動でアップロードしてください。", cover)

        # 各トラックの音源
        for track in tracks:
            audio = package_dir / "tracks" / Path(track.audio_path).name
            if audio.exists():
                self._safe_set_files(page, self.selectors["track_audio_input"], audio)
                logger.info("音源を投入: %s (%s)", track.brief.title, audio.name)

    def _submit(self, page, shots: Path) -> None:
        page.click(self.selectors["submit"])
        page.wait_for_load_state("networkidle")

    # --- helpers ---
    def _safe_fill(self, page, selector: str, value: str) -> None:
        try:
            page.fill(selector, value)
        except Exception as exc:
            logger.warning("fill 失敗 (%s): %s", selector, exc)

    def _safe_set_files(self, page, selector: str, path: Path) -> None:
        try:
            page.set_input_files(selector, str(path))
        except Exception as exc:
            logger.warning("set_input_files 失敗 (%s): %s", selector, exc)
