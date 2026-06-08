"""カバー画像バックエンド / プロンプト品質 / Playwright アップローダの単体テスト。"""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

import pytest

os.environ["MUSIC_PIPELINE_MOCK"] = "1"

from music_pipeline import prompting  # noqa: E402
from music_pipeline.config import Settings  # noqa: E402
from music_pipeline.cover_art import (  # noqa: E402
    GeminiCoverArtGenerator,
    LocalCoverArtGenerator,
    create_cover_generator,
)
from music_pipeline.distrokid_playwright import DistroKidPlaywrightUploader  # noqa: E402
from music_pipeline.models import Album  # noqa: E402


@pytest.fixture
def settings() -> Settings:
    s = Settings.load()
    s.force_mock = True
    return s


# ── プロンプト品質 ──
def test_style_prompt_has_guardrail_and_structure():
    style = prompting.build_style_prompt(
        genre="Synthwave", mood="dreamy", bpm=110, musical_key="A minor",
        instruments=["analog pads", "gated drums"], is_instrumental=False,
        vocal_type="warm female vocals",
    )
    assert "110 BPM" in style
    assert "warm female vocals" in style
    assert prompting.GUARDRAIL in style


def test_lyrics_scaffold_uses_suno_tags():
    lyrics = prompting.build_lyrics_scaffold(
        structure=["intro", "verse", "chorus", "bridge", "chorus", "outro"],
        mood="uplifting", theme="dawn", hook="my original hook",
    )
    assert "[Intro]" in lyrics
    assert "[Chorus]" in lyrics
    assert "my original hook" in lyrics


def test_instrumental_style_says_no_vocals():
    style = prompting.build_style_prompt(
        genre="Ambient", mood="calm", bpm=80, musical_key="C major",
        instruments=["pads"], is_instrumental=True,
    )
    assert "no vocals" in style


# ── カバー画像バックエンド ──
def test_cover_factory_uses_local_in_mock(settings: Settings):
    gen = create_cover_generator(settings)
    assert isinstance(gen, LocalCoverArtGenerator)


def test_cover_factory_gemini_when_backend_forced(settings: Settings):
    settings.raw.setdefault("cover", {})["backend"] = "gemini"
    gen = create_cover_generator(settings)
    assert isinstance(gen, GeminiCoverArtGenerator)


def test_gemini_cover_falls_back_to_local(settings: Settings, tmp_path: Path, monkeypatch):
    # 画像生成が失敗しても、必ずローカル生成にフォールバックしてファイルを残す
    gen = GeminiCoverArtGenerator(settings)
    monkeypatch.setattr(
        gen, "_render", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))
    )
    album = Album.new("Fallback Album", date(2026, 1, 1), [])
    out = gen.generate(album, tmp_path / "cov", style_hint="dreamy synthwave")
    assert out.exists()
    assert out.suffix in {".png", ".svg"}


# ── Playwright アップローダ（資格情報なしのガード）──
def test_uploader_requires_credentials(settings: Settings, tmp_path: Path, monkeypatch):
    monkeypatch.delenv("DISTROKID_EMAIL", raising=False)
    monkeypatch.delenv("DISTROKID_PASSWORD", raising=False)
    uploader = DistroKidPlaywrightUploader(settings)
    album = Album.new("X", date(2026, 1, 1), [])
    with pytest.raises(RuntimeError):
        uploader.upload(album, [], tmp_path)


def test_uploader_defaults_no_autosubmit(settings: Settings):
    uploader = DistroKidPlaywrightUploader(settings)
    assert uploader.auto_submit is False  # 既定は最終送信しない
