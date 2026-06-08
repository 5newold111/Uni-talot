"""設定の読み込み。`config/config.yaml` と環境変数 (.env) を統合する。"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

try:  # .env を読み込めるなら読む（無くても動く）
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover - dotenv 未導入でも動作させる
    pass


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = REPO_ROOT / "config" / "config.yaml"


def _env_bool(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class Settings:
    """パイプライン全体の設定。"""

    raw: dict[str, Any] = field(default_factory=dict)

    # --- 認証情報（環境変数）---
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    suno_api_key: str = ""
    suno_base_url: str = ""
    suno_poll_timeout: int = 300

    notify_email: str = ""
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""

    force_mock: bool = False

    # --- パス ---
    repo_root: Path = REPO_ROOT

    @classmethod
    def load(cls, config_path: Path | None = None) -> "Settings":
        path = config_path or DEFAULT_CONFIG_PATH
        raw: dict[str, Any] = {}
        if path.exists():
            raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

        return cls(
            raw=raw,
            gemini_api_key=os.getenv("GEMINI_API_KEY", "").strip(),
            gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash").strip(),
            suno_api_key=os.getenv("SUNO_API_KEY", "").strip(),
            suno_base_url=os.getenv("SUNO_BASE_URL", "").strip().rstrip("/"),
            suno_poll_timeout=int(os.getenv("SUNO_POLL_TIMEOUT", "300") or "300"),
            notify_email=os.getenv("NOTIFY_EMAIL", "").strip(),
            smtp_host=os.getenv("SMTP_HOST", "").strip(),
            smtp_port=int(os.getenv("SMTP_PORT", "587") or "587"),
            smtp_user=os.getenv("SMTP_USER", "").strip(),
            smtp_password=os.getenv("SMTP_PASSWORD", "").strip(),
            force_mock=_env_bool("MUSIC_PIPELINE_MOCK"),
        )

    # --- 派生プロパティ ---
    @property
    def gemini_mock(self) -> bool:
        """Gemini をモックで動かすべきか。"""
        return self.force_mock or not self.gemini_api_key

    @property
    def suno_mock(self) -> bool:
        """SUNO をモックで動かすべきか。"""
        return self.force_mock or not (self.suno_api_key and self.suno_base_url)

    def section(self, name: str) -> dict[str, Any]:
        return dict(self.raw.get(name, {}) or {})

    # よく使うショートカット
    @property
    def songs_per_day(self) -> int:
        return int(self.section("schedule").get("songs_per_day", 3))

    @property
    def release_days(self) -> list[int]:
        return list(self.section("schedule").get("release_days", [1, 15]))

    def _path(self, section: str, key: str, default: str) -> Path:
        value = self.section(section).get(key, default)
        p = Path(value)
        return p if p.is_absolute() else self.repo_root / p

    @property
    def tracks_dir(self) -> Path:
        return self._path("output", "tracks_dir", "output/tracks")

    @property
    def releases_dir(self) -> Path:
        return self._path("output", "releases_dir", "output/releases")

    @property
    def state_file(self) -> Path:
        return self._path("state", "file", "state/state.json")
