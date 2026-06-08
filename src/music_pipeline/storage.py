"""状態の永続化（生成済みトラック・アルバム・最終リリース日）。

シンプルな JSON ファイルで管理する。GitHub Actions の daily ワークフローが
このファイルをコミットすることで、実行間で状態が引き継がれる。
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Optional

from .models import Album, Track


class Store:
    def __init__(self, state_file: Path):
        self.state_file = state_file
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self._data = self._load()

    def _load(self) -> dict:
        if self.state_file.exists():
            try:
                return json.loads(self.state_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                pass
        return {"tracks": {}, "albums": {}, "last_release_date": None}

    def save(self) -> None:
        self.state_file.write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # --- tracks ---
    def add_track(self, track: Track) -> None:
        self._data["tracks"][track.id] = track.to_dict()

    def update_track(self, track: Track) -> None:
        self._data["tracks"][track.id] = track.to_dict()

    def get_track(self, track_id: str) -> Optional[Track]:
        d = self._data["tracks"].get(track_id)
        return Track.from_dict(d) if d else None

    def all_tracks(self) -> list[Track]:
        return [Track.from_dict(d) for d in self._data["tracks"].values()]

    def unreleased_tracks(self) -> list[Track]:
        return [
            t
            for t in self.all_tracks()
            if t.status == "generated" and not t.released
        ]

    # --- albums ---
    def add_album(self, album: Album) -> None:
        self._data["albums"][album.id] = album.to_dict()

    def all_albums(self) -> list[Album]:
        return [Album.from_dict(d) for d in self._data["albums"].values()]

    # --- release bookkeeping ---
    @property
    def last_release_date(self) -> Optional[str]:
        return self._data.get("last_release_date")

    def set_last_release_date(self, d: date) -> None:
        self._data["last_release_date"] = d.isoformat()

    def mark_released(self, track_ids: list[str], release_id: str) -> None:
        for tid in track_ids:
            if tid in self._data["tracks"]:
                self._data["tracks"][tid]["released"] = True
                self._data["tracks"][tid]["release_id"] = release_id
