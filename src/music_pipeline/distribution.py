"""配信パッケージ化（DistroKid 半自動）。

DistroKid は公式アップロード API が無いため、配信に必要な成果物
（音源・カバー・メタデータ CSV・手順書）を 1 つのフォルダに整える。
最後の「DistroKid 画面でのアップロード」だけ人手で行う。
"""

from __future__ import annotations

import shutil
from pathlib import Path

from .config import Settings
from .cover_art import CoverArtGenerator
from .metadata import MetadataBuilder
from .models import Album, Track


class DistributionPackager:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.label = settings.section("label")
        self.metadata = MetadataBuilder(settings)
        self.cover = CoverArtGenerator()

    def package(self, album: Album, tracks: list[Track]) -> Path:
        release_dir = self.settings.releases_dir / album.id
        tracks_out = release_dir / "tracks"
        tracks_out.mkdir(parents=True, exist_ok=True)

        # 1) 音源をパッケージへコピー
        for track in tracks:
            if track.audio_path and Path(track.audio_path).exists():
                shutil.copy2(track.audio_path, tracks_out / Path(track.audio_path).name)

        # 2) カバーアート
        cover_path = self.cover.generate(
            album, release_dir / "cover.svg", artist=self.label.get("artist_name", "AI Sound Lab")
        )
        album.cover_path = str(cover_path)

        # 3) メタデータ CSV
        self.metadata.write_csv(album, tracks, release_dir / "distrokid_metadata.csv")

        # 4) アップロード手順書
        self._write_instructions(album, tracks, release_dir)

        album.package_dir = str(release_dir)
        return release_dir

    def _write_instructions(self, album: Album, tracks: list[Track], release_dir: Path) -> None:
        artist = self.label.get("artist_name", "AI Sound Lab")
        lines = [
            f"# DistroKid アップロード手順 — {album.title}",
            "",
            f"- アーティスト名: **{artist}**",
            f"- アルバム名: **{album.title}**",
            f"- リリース日: **{album.release_date}**",
            f"- トラック数: **{len(tracks)}**",
            "",
            "## 手順（半自動の最終ステップ）",
            "",
            "1. https://distrokid.com にログイン。",
            "2. **Upload** から新規リリースを作成。",
            "3. カバーアート（`cover.svg`）を 3000x3000 の JPG/PNG に変換してアップロード。",
            "   - SVG は本番用に PNG/JPG へ変換してください（例: `rsvg-convert` / オンライン変換）。",
            "4. `distrokid_metadata.csv` を参照し、各トラックの情報を入力。",
            "5. `tracks/` 内の音源を順番どおりにアップロード。",
            "6. 配信先（Spotify / Apple Music / YouTube Music 等）を選択して提出。",
            "",
            "## トラック一覧",
            "",
        ]
        for i, track in enumerate(tracks, start=1):
            b = track.brief
            kind = "instrumental" if b.is_instrumental else b.language
            fname = Path(track.audio_path).name if track.audio_path else "(missing)"
            lines.append(f"{i}. **{b.title}** — {b.genre} / {b.mood} / {b.bpm}BPM / {kind} — `{fname}`")
        lines.append("")
        lines.append("> AI 生成楽曲の配信可否・表記要件は各ストアの最新ポリシーを確認してください。")
        (release_dir / "UPLOAD_INSTRUCTIONS.md").write_text("\n".join(lines), encoding="utf-8")
