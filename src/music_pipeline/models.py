"""パイプライン全体で受け渡すデータモデル。"""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field, fields
from datetime import date, datetime
from typing import Any


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def _filter_known(cls, d: dict[str, Any]) -> dict[str, Any]:
    """dataclass に存在するフィールドだけを残す（前方/後方互換のため）。"""
    known = {f.name for f in fields(cls)}
    return {k: v for k, v in d.items() if k in known}


@dataclass
class TrendProfile:
    """著作権セーフな、抽象的トレンドのスナップショット。

    既存楽曲そのものではなく、ジャンル/テンポ/ムードの「傾向」を表す。
    """

    captured_at: str
    genres: list[str] = field(default_factory=list)
    bpm_range: list[int] = field(default_factory=lambda: [80, 130])
    moods: list[str] = field(default_factory=list)
    instrumentation_trends: list[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "TrendProfile":
        return cls(**d)


@dataclass
class CreativeBrief:
    """1 曲ぶんのオリジナル創作指示。"""

    id: str
    title: str
    genre: str
    mood: str
    bpm: int
    musical_key: str
    instruments: list[str] = field(default_factory=list)
    structure: list[str] = field(default_factory=list)  # 例: ["intro", "verse", "chorus"]
    theme: str = ""
    is_instrumental: bool = False
    language: str = "Instrumental"
    # --- 品質チューニング用の追加属性（任意）---
    sub_genre: str = ""
    vocal_type: str = ""
    production_notes: str = ""
    energy_arc: str = ""
    hook: str = ""
    suno_style_prompt: str = ""   # SUNO の style/description 欄へ
    suno_lyrics_prompt: str = ""  # SUNO の lyrics 欄へ（インストなら空）
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    @staticmethod
    def new(**kwargs: Any) -> "CreativeBrief":
        kwargs.setdefault("id", _new_id("brief"))
        return CreativeBrief(**kwargs)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "CreativeBrief":
        return cls(**_filter_known(cls, d))


@dataclass
class Track:
    """生成済みの 1 曲。"""

    id: str
    brief: CreativeBrief
    status: str = "pending"  # pending | generated | failed
    audio_path: str = ""
    suno_clip_id: str = ""
    duration_seconds: int = 0
    released: bool = False
    release_id: str = ""
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    @staticmethod
    def new(brief: CreativeBrief) -> "Track":
        return Track(id=_new_id("track"), brief=brief)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["brief"] = self.brief.to_dict()
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Track":
        d = _filter_known(cls, dict(d))
        d["brief"] = CreativeBrief.from_dict(d["brief"])
        return cls(**d)


@dataclass
class Album:
    """リリース単位のアルバム。"""

    id: str
    title: str
    release_date: str  # ISO date
    track_ids: list[str] = field(default_factory=list)
    cover_path: str = ""
    package_dir: str = ""
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    @staticmethod
    def new(title: str, release_date: date, track_ids: list[str]) -> "Album":
        return Album(
            id=_new_id("album"),
            title=title,
            release_date=release_date.isoformat(),
            track_ids=list(track_ids),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Album":
        return cls(**_filter_known(cls, d))
