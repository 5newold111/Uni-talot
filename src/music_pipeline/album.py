"""アルバム集約：前回リリース以降に生成された未配信トラックをまとめる。"""

from __future__ import annotations

from datetime import date

from .models import Album, Track


class AlbumAssembler:
    def assemble(self, tracks: list[Track], release_date: date) -> Album:
        """未配信トラックから 1 枚のアルバムを構成する。"""
        title = self._album_title(release_date)
        # 生成順（created_at）でトラック順を安定化
        ordered = sorted(tracks, key=lambda t: t.created_at)
        return Album.new(title, release_date, [t.id for t in ordered])

    @staticmethod
    def _album_title(release_date: date) -> str:
        half = "I" if release_date.day <= 14 else "II"
        return f"{release_date.strftime('%Y-%m')} Vol.{half}"
