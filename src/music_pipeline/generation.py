"""SUNO（非公式 API）による楽曲生成クライアント。

SUNO は公式 API を一般提供していないため、コミュニティ製のラッパー
（自己ホスト型プロキシ等）を `SUNO_BASE_URL` 経由で利用することを想定。
一般的な「生成依頼 → ポーリング → 音源 URL 取得 → ダウンロード」フローを実装する。
利用するラッパーの仕様に合わせて、エンドポイント名やレスポンスのキーを調整すること。

キー未設定時は無音に近いダミー WAV を出力するモードにフォールバックする。
"""

from __future__ import annotations

import logging
import struct
import time
import wave
from pathlib import Path

from .config import Settings
from .models import CreativeBrief, Track

logger = logging.getLogger(__name__)


class SunoClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.gen_cfg = settings.section("generation")
        self.tracks_dir = settings.tracks_dir
        self.tracks_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, brief: CreativeBrief) -> Track:
        track = Track.new(brief)
        try:
            if self.settings.suno_mock:
                self._generate_mock(track)
            else:
                self._generate_real(track)
            track.status = "generated"
        except Exception as exc:  # pragma: no cover - 実 API 失敗時
            logger.exception("Generation failed for brief %s: %s", brief.id, exc)
            track.status = "failed"
        return track

    # --- mock: ダミー音源（短い無音 WAV）を書き出す ---
    def _generate_mock(self, track: Track) -> None:
        duration = int(self.gen_cfg.get("duration_seconds", 120))
        path = self.tracks_dir / f"{track.id}.wav"
        framerate = 8000
        # 容量を抑えるため実際は 1 秒だけ書き、duration はメタとして持つ
        n_frames = framerate
        with wave.open(str(path), "w") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(framerate)
            silence = struct.pack("<" + "h" * n_frames, *([0] * n_frames))
            w.writeframes(silence)
        track.audio_path = str(path)
        track.suno_clip_id = f"mock_{track.id}"
        track.duration_seconds = duration
        logger.info("[mock] generated track %s -> %s", track.id, path)

    # --- real: 非公式 API ラッパー ---
    def _generate_real(self, track: Track) -> None:
        import requests

        base = self.settings.suno_base_url
        headers = {"Authorization": f"Bearer {self.settings.suno_api_key}"}
        brief = track.brief

        payload = {
            "prompt": brief.suno_lyrics_prompt or brief.theme,
            "tags": brief.suno_style_prompt or brief.genre,
            "title": brief.title,
            "make_instrumental": brief.is_instrumental,
            "model": self.gen_cfg.get("model_hint", "v4"),
            "wait_audio": False,
        }
        # 1) 生成依頼
        resp = requests.post(f"{base}/api/generate", json=payload, headers=headers, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        clip = data[0] if isinstance(data, list) else data
        clip_id = clip.get("id") or clip.get("clip_id", "")
        track.suno_clip_id = clip_id

        # 2) 完了までポーリング
        audio_url = self._poll_for_audio(base, headers, clip_id)

        # 3) ダウンロード
        path = self.tracks_dir / f"{track.id}.mp3"
        audio = requests.get(audio_url, timeout=120)
        audio.raise_for_status()
        path.write_bytes(audio.content)
        track.audio_path = str(path)
        track.duration_seconds = int(self.gen_cfg.get("duration_seconds", 120))
        logger.info("generated track %s -> %s", track.id, path)

    def _poll_for_audio(self, base: str, headers: dict, clip_id: str) -> str:
        import requests

        deadline = time.time() + self.settings.suno_poll_timeout
        while time.time() < deadline:
            r = requests.get(f"{base}/api/get", params={"ids": clip_id}, headers=headers, timeout=30)
            r.raise_for_status()
            data = r.json()
            clip = data[0] if isinstance(data, list) else data
            status = clip.get("status", "")
            audio_url = clip.get("audio_url") or clip.get("audio")
            if status in {"complete", "streaming"} and audio_url:
                return audio_url
            time.sleep(5)
        raise TimeoutError(f"SUNO generation timed out for clip {clip_id}")
