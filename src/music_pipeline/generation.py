"""SUNO（非公式 API）による楽曲生成クライアント。

SUNO は公式 API を一般提供していないため、コミュニティで広く使われている
自己ホスト型ラッパー（例: `gcui-art/suno-api`）の事実上の標準エンドポイントに
合わせて実装している:

  - POST /api/custom_generate  … 歌詞(prompt)+スタイル(tags)+タイトルを指定
  - POST /api/generate         … 説明文(prompt)のみ（自動作詞）
  - GET  /api/get?ids=<id>     … 生成状況のポーリング
  - GET  /api/get_limit        … クレジット残量

別のラッパーを使う場合は config.yaml の generation.endpoints で
パスを上書きできる。キー未設定時は無音に近いダミー WAV を出力する。
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

DEFAULT_ENDPOINTS = {
    "custom_generate": "/api/custom_generate",
    "generate": "/api/generate",
    "get": "/api/get",
    "get_limit": "/api/get_limit",
}


class SunoClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.gen_cfg = settings.section("generation")
        self.endpoints = {**DEFAULT_ENDPOINTS, **(self.gen_cfg.get("endpoints") or {})}
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
        model = self.gen_cfg.get("model_hint", "v4")

        # 歌詞があれば custom_generate、無ければ description ベースの generate
        if brief.suno_lyrics_prompt and not brief.is_instrumental:
            url = base + self.endpoints["custom_generate"]
            payload = {
                "prompt": brief.suno_lyrics_prompt,  # custom では prompt=歌詞
                "tags": brief.suno_style_prompt or brief.genre,
                "title": brief.title,
                "make_instrumental": False,
                "model": model,
                "wait_audio": False,
            }
        else:
            url = base + self.endpoints["generate"]
            payload = {
                "prompt": brief.suno_style_prompt or brief.theme,  # generate では prompt=説明文
                "make_instrumental": brief.is_instrumental,
                "model": model,
                "wait_audio": False,
            }

        resp = requests.post(url, json=payload, headers=headers, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        clip = data[0] if isinstance(data, list) else data
        clip_id = clip.get("id") or clip.get("clip_id", "")
        if not clip_id:
            raise RuntimeError(f"No clip id in SUNO response: {data!r}")
        track.suno_clip_id = clip_id

        audio_url = self._poll_for_audio(base, headers, clip_id)

        # ダウンロード
        path = self.tracks_dir / f"{track.id}.mp3"
        audio = requests.get(audio_url, timeout=120)
        audio.raise_for_status()
        path.write_bytes(audio.content)
        track.audio_path = str(path)
        track.duration_seconds = int(self.gen_cfg.get("duration_seconds", 120))
        logger.info("generated track %s -> %s", track.id, path)

    def _poll_for_audio(self, base: str, headers: dict, clip_id: str) -> str:
        import requests

        url = base + self.endpoints["get"]
        deadline = time.time() + self.settings.suno_poll_timeout
        last_status = ""
        while time.time() < deadline:
            r = requests.get(url, params={"ids": clip_id}, headers=headers, timeout=30)
            r.raise_for_status()
            data = r.json()
            clip = data[0] if isinstance(data, list) else data
            status = clip.get("status", "")
            if status != last_status:
                logger.info("SUNO clip %s status: %s", clip_id, status)
                last_status = status
            audio_url = clip.get("audio_url") or clip.get("audio")
            if status in {"complete", "streaming"} and audio_url:
                return audio_url
            if status == "error":
                raise RuntimeError(f"SUNO reported error for clip {clip_id}: {clip!r}")
            time.sleep(5)
        raise TimeoutError(f"SUNO generation timed out for clip {clip_id}")
