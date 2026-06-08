"""個別コンポーネントのテスト（モックモード、外部 API 不要）。"""

from __future__ import annotations

import csv
import os
from datetime import date
from pathlib import Path

import pytest

os.environ["MUSIC_PIPELINE_MOCK"] = "1"

from music_pipeline.config import Settings  # noqa: E402
from music_pipeline.cover_art import CoverArtGenerator  # noqa: E402
from music_pipeline.generation import SunoClient  # noqa: E402
from music_pipeline.metadata import MetadataBuilder  # noqa: E402
from music_pipeline.models import Album  # noqa: E402
from music_pipeline.trend_analysis import BriefGenerator, TrendAnalyzer  # noqa: E402


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    s = Settings.load()
    s.force_mock = True
    s.raw.setdefault("output", {})
    s.raw["output"]["tracks_dir"] = str(tmp_path / "tracks")
    s.raw["output"]["releases_dir"] = str(tmp_path / "releases")
    s.raw.setdefault("state", {})
    s.raw["state"]["file"] = str(tmp_path / "state.json")
    return s


def _briefs(settings: Settings, n: int):
    profile = TrendAnalyzer(settings).analyze()
    return BriefGenerator(settings).generate(profile, n)


def test_instrumental_split_matches_ratio(settings: Settings):
    settings.raw.setdefault("generation", {})["instrumental_ratio"] = 0.5
    briefs = _briefs(settings, 4)
    instrumental = [b for b in briefs if b.is_instrumental]
    assert len(instrumental) == 2
    # 歌あり曲は言語が "Instrumental" にならない
    for b in briefs:
        if not b.is_instrumental:
            assert b.language.lower() != "instrumental"
            assert b.suno_lyrics_prompt
        else:
            assert b.language == "Instrumental"
            assert b.suno_lyrics_prompt == ""


def test_cover_art_generates_file(settings: Settings, tmp_path: Path):
    album = Album.new("Test Album", date(2026, 1, 1), [])
    out = CoverArtGenerator().generate(album, tmp_path / "cov")
    assert out.exists()
    assert out.suffix in {".png", ".svg"}


def test_metadata_csv_consistency(settings: Settings, tmp_path: Path):
    suno = SunoClient(settings)
    briefs = _briefs(settings, 3)
    tracks = [suno.generate(b) for b in briefs]
    album = Album.new("CSV Album", date(2026, 1, 1), [t.id for t in tracks])
    out = MetadataBuilder(settings).write_csv(album, tracks, tmp_path / "meta.csv")

    with out.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 3
    for row in rows:
        # 歌あり/インストの整合（language が Instrumental ⇔ is_instrumental yes）
        if row["is_instrumental"] == "yes":
            assert row["language"] == "Instrumental"
        else:
            assert row["language"] != "Instrumental"
        assert row["audio_file"].endswith(".wav")


def test_suno_mock_produces_audio(settings: Settings):
    suno = SunoClient(settings)
    brief = _briefs(settings, 1)[0]
    track = suno.generate(brief)
    assert track.status == "generated"
    assert Path(track.audio_path).exists()
    assert track.duration_seconds > 0
