"""Gemini を使ったトレンド分析と創作ブリーフ生成。

著作権セーフ設計:
- 既存の特定楽曲（音源・歌詞・メロディ）は一切入力しない。
- 扱うのはジャンル/テンポ/ムード/楽器構成といった「抽象的な傾向」のみ。
- 生成プロンプトに「オリジナルであること」「実在の曲・人名を参照しないこと」を明記。

API キーが無い場合は決定論的なモック出力にフォールバックする。
"""

from __future__ import annotations

import json
import logging
import random
from datetime import datetime

from .config import Settings
from .models import CreativeBrief, TrendProfile

logger = logging.getLogger(__name__)


# 既存表現の流用を防ぐためのシステム指示（両工程で共有）
_COPYRIGHT_GUARDRAIL = (
    "You must produce only ORIGINAL, abstract creative direction. "
    "Never reference, name, imitate, or paraphrase any real existing song, "
    "artist, band, lyric, or trademark. Work only at the level of genre, tempo, "
    "mood, and instrumentation conventions (which are facts/ideas, not protected "
    "expression). Do not produce anything that could be a derivative of a "
    "specific copyrighted work."
)


class TrendAnalyzer:
    """公開トレンドの抽象的スナップショットを作る。"""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.trend_cfg = settings.section("trend")

    def analyze(self) -> TrendProfile:
        if self.settings.gemini_mock:
            return self._mock_profile()
        try:
            return self._gemini_profile()
        except Exception as exc:  # pragma: no cover - 実 API 失敗時の保険
            logger.warning("Gemini trend analysis failed (%s); falling back to mock", exc)
            return self._mock_profile()

    # --- mock ---
    def _mock_profile(self) -> TrendProfile:
        return TrendProfile(
            captured_at=datetime.utcnow().isoformat(),
            genres=list(self.trend_cfg.get("target_genres", ["Lo-Fi Hip Hop"])),
            bpm_range=list(self.trend_cfg.get("bpm_range", [80, 130])),
            moods=list(self.trend_cfg.get("moods", ["chill", "uplifting"])),
            instrumentation_trends=[
                "warm analog synth pads",
                "soft electric piano",
                "lo-fi drum textures",
                "mellow bass",
            ],
            notes="[mock] 抽象的なトレンドのダミー。設定 config.yaml の trend 由来。",
        )

    # --- gemini ---
    def _gemini_profile(self) -> TrendProfile:
        import google.generativeai as genai

        genai.configure(api_key=self.settings.gemini_api_key)
        model = genai.GenerativeModel(self.settings.gemini_model)

        genres = self.trend_cfg.get("target_genres", [])
        prompt = (
            f"{_COPYRIGHT_GUARDRAIL}\n\n"
            "Summarize, at an ABSTRACT level only, current general trends for these "
            f"genres: {genres}. Output strict JSON with keys: "
            "genres (list[str]), bpm_range ([min,max] ints), moods (list[str]), "
            "instrumentation_trends (list[str]), notes (str). "
            "Do NOT mention any specific song, artist, or release."
        )
        resp = model.generate_content(prompt)
        data = _extract_json(resp.text)
        return TrendProfile(
            captured_at=datetime.utcnow().isoformat(),
            genres=data.get("genres", genres),
            bpm_range=data.get("bpm_range", self.trend_cfg.get("bpm_range", [80, 130])),
            moods=data.get("moods", self.trend_cfg.get("moods", [])),
            instrumentation_trends=data.get("instrumentation_trends", []),
            notes=data.get("notes", ""),
        )


class BriefGenerator:
    """TrendProfile から n 件のオリジナル創作ブリーフを生成する。"""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.label = settings.section("label")
        self.gen_cfg = settings.section("generation")

    def generate(self, profile: TrendProfile, n: int) -> list[CreativeBrief]:
        if self.settings.gemini_mock:
            return [self._mock_brief(profile, i, n) for i in range(n)]
        try:
            return self._gemini_briefs(profile, n)
        except Exception as exc:  # pragma: no cover
            logger.warning("Gemini brief generation failed (%s); using mock", exc)
            return [self._mock_brief(profile, i, n) for i in range(n)]

    def _is_instrumental(self, index: int, n: int) -> bool:
        ratio = float(self.gen_cfg.get("instrumental_ratio", 0.5))
        # 先頭から ratio の割合をインスト曲に。決定論的でモックでも再現可能。
        return index < round(ratio * n)

    def _lyric_language(self, is_instrumental: bool) -> str:
        if is_instrumental:
            return "Instrumental"
        lang = self.label.get("language", "English")
        # 設定が "Instrumental" のまま歌あり曲になった場合の保険
        return "English" if lang.lower() == "instrumental" else lang

    # --- mock ---
    def _mock_brief(self, profile: TrendProfile, index: int, n: int) -> CreativeBrief:
        rng = random.Random(f"{profile.captured_at}:{index}")
        genre = rng.choice(profile.genres or ["Lo-Fi Hip Hop"])
        mood = rng.choice(profile.moods or ["chill"])
        lo, hi = (profile.bpm_range + [80, 130])[:2]
        bpm = rng.randint(int(lo), int(hi))
        key = rng.choice(["C major", "A minor", "G major", "E minor", "F major"])
        instrumental = self._is_instrumental(index, n)
        title = self._mock_title(rng, mood, genre)
        instruments = (profile.instrumentation_trends or ["synth pad", "piano", "drums"])[:4]
        style = f"{mood} {genre}, {bpm} BPM, {key}, " + ", ".join(instruments)
        return CreativeBrief.new(
            title=title,
            genre=genre,
            mood=mood,
            bpm=bpm,
            musical_key=key,
            instruments=instruments,
            structure=["intro", "verse", "chorus", "verse", "chorus", "outro"],
            theme=f"an original {mood} mood piece",
            is_instrumental=instrumental,
            language=self._lyric_language(instrumental),
            suno_style_prompt=style + " — original, no references to existing works",
            suno_lyrics_prompt="" if instrumental else self._mock_lyrics(mood),
        )

    @staticmethod
    def _mock_title(rng: random.Random, mood: str, genre: str) -> str:
        words_a = ["Midnight", "Neon", "Velvet", "Distant", "Paper", "Golden", "Quiet"]
        words_b = ["Tides", "Echoes", "Skyline", "Garden", "Signal", "Mirage", "Drift"]
        return f"{rng.choice(words_a)} {rng.choice(words_b)}"

    @staticmethod
    def _mock_lyrics(mood: str) -> str:
        return (
            "[Verse]\nOriginal placeholder lyric line one\nOriginal placeholder lyric line two\n"
            "[Chorus]\nAn original hook for a "
            f"{mood} song\n"
        )

    # --- gemini ---
    def _gemini_briefs(self, profile: TrendProfile, n: int) -> list[CreativeBrief]:
        import google.generativeai as genai

        genai.configure(api_key=self.settings.gemini_api_key)
        model = genai.GenerativeModel(self.settings.gemini_model)

        prompt = (
            f"{_COPYRIGHT_GUARDRAIL}\n\n"
            f"Using ONLY this abstract trend profile:\n{json.dumps(profile.to_dict())}\n\n"
            f"Invent {n} ORIGINAL song concepts. Each must be wholly original and must "
            "NOT resemble or reference any specific existing song/artist. "
            "Return strict JSON: a list of objects with keys: title, genre, mood, "
            "bpm (int), musical_key, instruments (list[str]), structure (list[str]), "
            "theme, is_instrumental (bool), suno_style_prompt, suno_lyrics_prompt "
            "(empty if instrumental)."
        )
        resp = model.generate_content(prompt)
        items = _extract_json(resp.text)
        if isinstance(items, dict):
            items = items.get("songs") or items.get("items") or [items]

        briefs: list[CreativeBrief] = []
        for i, item in enumerate(items[:n]):
            instrumental = bool(item.get("is_instrumental", self._is_instrumental(i, n)))
            briefs.append(
                CreativeBrief.new(
                    title=item.get("title", f"Untitled {i + 1}"),
                    genre=item.get("genre", "Electronic"),
                    mood=item.get("mood", "chill"),
                    bpm=int(item.get("bpm", 100)),
                    musical_key=item.get("musical_key", "C major"),
                    instruments=item.get("instruments", []),
                    structure=item.get("structure", ["intro", "verse", "chorus"]),
                    theme=item.get("theme", ""),
                    is_instrumental=instrumental,
                    language=self._lyric_language(instrumental),
                    suno_style_prompt=item.get("suno_style_prompt", ""),
                    suno_lyrics_prompt="" if instrumental else item.get("suno_lyrics_prompt", ""),
                )
            )
        # 万一足りなければモックで補完
        while len(briefs) < n:
            briefs.append(self._mock_brief(profile, len(briefs), n))
        return briefs


def _extract_json(text: str):
    """LLM 出力から JSON 部分を頑健に取り出す。"""
    text = (text or "").strip()
    if text.startswith("```"):
        # ```json ... ``` のフェンスを除去
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip("` \n")
    # 最初の { または [ から末尾の対応する括弧まで
    for opener, closer in (("{", "}"), ("[", "]")):
        start = text.find(opener)
        end = text.rfind(closer)
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                continue
    return json.loads(text)
