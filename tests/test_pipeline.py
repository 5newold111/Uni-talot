"""モックモードでのエンドツーエンド動作テスト。外部 API 不要。"""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

import pytest

os.environ["MUSIC_PIPELINE_MOCK"] = "1"

from music_pipeline.config import Settings  # noqa: E402
from music_pipeline.pipeline import Pipeline  # noqa: E402
from music_pipeline.trend_analysis import BriefGenerator, TrendAnalyzer  # noqa: E402


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    s = Settings.load()
    s.force_mock = True
    # 出力・状態を tmp に隔離
    s.raw.setdefault("output", {})
    s.raw["output"]["tracks_dir"] = str(tmp_path / "tracks")
    s.raw["output"]["releases_dir"] = str(tmp_path / "releases")
    s.raw.setdefault("state", {})
    s.raw["state"]["file"] = str(tmp_path / "state.json")
    return s


def test_trend_and_briefs(settings: Settings):
    profile = TrendAnalyzer(settings).analyze()
    assert profile.genres
    briefs = BriefGenerator(settings).generate(profile, 3)
    assert len(briefs) == 3
    for b in briefs:
        assert b.title
        assert b.bpm > 0
        assert b.suno_style_prompt
        # 著作権ガードレール: スタイルにオリジナル指示が含まれる
        assert "original" in b.suno_style_prompt.lower()


def test_daily_generation(settings: Settings):
    pipeline = Pipeline(settings)
    ids = pipeline.run_daily(count=3)
    assert len(ids) == 3
    tracks = pipeline.store.all_tracks()
    assert len(tracks) == 3
    for t in tracks:
        assert t.status == "generated"
        assert Path(t.audio_path).exists()


def test_release_packaging(settings: Settings):
    pipeline = Pipeline(settings)
    pipeline.run_daily(count=3)
    album = pipeline.run_release(release_date=date(2026, 1, 1), force=True)
    assert album is not None
    pkg = Path(album.package_dir)
    assert (pkg / "distrokid_metadata.csv").exists()
    assert (pkg / "UPLOAD_INSTRUCTIONS.md").exists()
    assert (pkg / "cover.svg").exists()
    assert (pkg / "tracks").is_dir()
    # 配信後は未配信トラックが無くなる
    assert pipeline.store.unreleased_tracks() == []


def test_release_skips_non_release_day(settings: Settings):
    pipeline = Pipeline(settings)
    pipeline.run_daily(count=1)
    # リリース日でない & force なし → None
    album = pipeline.run_release(release_date=date(2026, 1, 7), force=False)
    assert album is None
