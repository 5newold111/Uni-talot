"""日次生成・アルバムリリースのオーケストレーション。"""

from __future__ import annotations

import logging
from datetime import date, datetime

from .album import AlbumAssembler
from .config import Settings
from .distribution import DistributionPackager
from .generation import SunoClient
from .models import Album
from .notify import Notifier
from .storage import Store
from .trend_analysis import BriefGenerator, TrendAnalyzer

logger = logging.getLogger(__name__)


class Pipeline:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or Settings.load()
        self.store = Store(self.settings.state_file)

    # ── 日次：3 曲生成 ──
    def run_daily(self, count: int | None = None) -> list[str]:
        n = count or self.settings.songs_per_day
        logger.info("=== Daily generation: %d songs (mock: gemini=%s suno=%s) ===",
                    n, self.settings.gemini_mock, self.settings.suno_mock)

        analyzer = TrendAnalyzer(self.settings)
        brief_gen = BriefGenerator(self.settings)
        suno = SunoClient(self.settings)

        profile = analyzer.analyze()
        briefs = brief_gen.generate(profile, n)

        generated_ids: list[str] = []
        for brief in briefs:
            track = suno.generate(brief)
            self.store.add_track(track)
            if track.status == "generated":
                generated_ids.append(track.id)
            logger.info("  - %s [%s] %s", brief.title, track.status, track.audio_path)

        self.store.save()
        logger.info("=== Daily done: %d/%d generated ===", len(generated_ids), n)
        return generated_ids

    # ── リリース：アルバム化して配信パッケージを作る ──
    def run_release(self, release_date: date | None = None, force: bool = False) -> Album | None:
        today = release_date or date.today()
        if not force and today.day not in self.settings.release_days:
            logger.info("Today (%s) is not a release day %s; skipping.",
                        today.isoformat(), self.settings.release_days)
            return None

        tracks = self.store.unreleased_tracks()
        if not tracks:
            logger.info("No unreleased tracks to release.")
            return None

        logger.info("=== Release: %d tracks ===", len(tracks))
        album = AlbumAssembler().assemble(tracks, today)
        packager = DistributionPackager(self.settings)
        release_dir = packager.package(album, tracks)

        self.store.add_album(album)
        self.store.mark_released([t.id for t in tracks], album.id)
        self.store.set_last_release_date(today)
        self.store.save()

        Notifier(self.settings).send(
            subject=f"[AI Music] アルバム '{album.title}' を配信パッケージ化しました",
            body=(
                f"アルバム: {album.title}\n"
                f"トラック数: {len(tracks)}\n"
                f"パッケージ: {release_dir}\n\n"
                f"DistroKid にログインし、{release_dir}/UPLOAD_INSTRUCTIONS.md に従って\n"
                f"最終アップロードを行ってください（半自動配信の最終ステップ）。\n"
            ),
        )
        logger.info("=== Release done: %s -> %s ===", album.title, release_dir)
        return album


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
