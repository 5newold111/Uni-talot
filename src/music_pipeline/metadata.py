"""DistroKid 向けメタデータ（トラック一覧 CSV）の生成。

DistroKid には公式アップロード API が無いため、人が画面入力する際の
リファレンスとなる CSV を出力する（半自動運用）。
列構成は DistroKid の入力項目に概ね対応させてある。
"""

from __future__ import annotations

import csv
from pathlib import Path

from .config import Settings
from .models import Album, Track

CSV_FIELDS = [
    "track_number",
    "title",
    "artist",
    "album",
    "genre",
    "language",
    "is_instrumental",
    "explicit",
    "isrc",            # 空ならストア側で自動採番
    "release_date",
    "audio_file",
]


class MetadataBuilder:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.label = settings.section("label")

    def write_csv(self, album: Album, tracks: list[Track], out_path: Path) -> Path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
            writer.writeheader()
            for i, track in enumerate(tracks, start=1):
                b = track.brief
                writer.writerow(
                    {
                        "track_number": i,
                        "title": b.title,
                        "artist": self.label.get("artist_name", "AI Sound Lab"),
                        "album": album.title,
                        "genre": b.genre,
                        "language": b.language,
                        "is_instrumental": "yes" if b.is_instrumental else "no",
                        "explicit": "yes" if self.label.get("explicit") else "no",
                        "isrc": "",
                        "release_date": album.release_date,
                        "audio_file": Path(track.audio_path).name if track.audio_path else "",
                    }
                )
        return out_path
