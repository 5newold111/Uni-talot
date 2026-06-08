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

from . import prompting
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

# ブリーフ生成のシステムプロンプト（品質チューニング）
_BRIEF_SYSTEM_PROMPT = (
    "You are a professional songwriter and music producer creating briefs for an "
    "AI music generator (SUNO).\n"
    f"{_COPYRIGHT_GUARDRAIL}\n\n"
    "Quality rules:\n"
    "- Craft a memorable, singable hook and a clear emotional arc.\n"
    "- Use concrete, sensory, original imagery in lyrics; avoid clichés and filler.\n"
    "- Keep verses and choruses with consistent meter and natural rhyme.\n"
    "- Structure lyrics with SUNO section tags: [Intro], [Verse], [Pre-Chorus], "
    "[Chorus], [Bridge], [Outro].\n"
    "- The style description should name genre, sub-genre, tempo, key, instrumentation, "
    "vocal character, production texture, and energy arc.\n"
    "- Everything must be 100% original. Never reproduce real lyrics/titles/artists.\n"
    "- Output STRICT JSON only, no prose, no code fences."
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

    # --- スタイル/歌詞の組み立てを一元化（モック/Gemini 共通で品質を担保）---
    def _assemble_brief(
        self,
        *,
        rng: random.Random,
        title: str,
        genre: str,
        mood: str,
        bpm: int,
        key: str,
        instruments: list[str],
        structure: list[str],
        theme: str,
        instrumental: bool,
        sub_genre: str = "",
        vocal_type: str = "",
        production_notes: str = "",
        energy_arc: str = "",
        hook: str = "",
        lyrics_body: str | None = None,
    ) -> CreativeBrief:
        language = self._lyric_language(instrumental)
        style = prompting.build_style_prompt(
            genre=genre,
            mood=mood,
            bpm=bpm,
            musical_key=key,
            instruments=instruments,
            is_instrumental=instrumental,
            sub_genre=sub_genre,
            vocal_type=vocal_type,
            production_notes=production_notes,
            energy_arc=energy_arc,
            rng=rng,
        )
        if instrumental:
            lyrics = ""
        elif lyrics_body and lyrics_body.strip():
            lyrics = lyrics_body.strip() + "\n"
        else:
            lyrics = prompting.build_lyrics_scaffold(
                structure=structure, mood=mood, theme=theme, hook=hook,
                language=language, rng=rng,
            )
        return CreativeBrief.new(
            title=title,
            genre=genre,
            mood=mood,
            bpm=bpm,
            musical_key=key,
            instruments=instruments,
            structure=structure,
            theme=theme,
            is_instrumental=instrumental,
            language=language,
            sub_genre=sub_genre,
            vocal_type="" if instrumental else (vocal_type or ""),
            production_notes=production_notes,
            energy_arc=energy_arc,
            hook="" if instrumental else hook,
            suno_style_prompt=style,
            suno_lyrics_prompt=lyrics,
        )

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
        return self._assemble_brief(
            rng=rng,
            title=title,
            genre=genre,
            mood=mood,
            bpm=bpm,
            key=key,
            instruments=instruments,
            structure=["intro", "verse", "pre-chorus", "chorus", "verse", "chorus", "bridge", "chorus", "outro"],
            theme=f"an original {mood} reflection",
            instrumental=instrumental,
            sub_genre=rng.choice(["downtempo", "dream pop", "future garage", "chillwave", ""]),
            vocal_type=rng.choice(prompting.VOCAL_TYPES),
            production_notes=rng.choice(prompting.PRODUCTION_DESCRIPTORS),
            energy_arc=rng.choice(prompting.ENERGY_ARCS),
        )

    @staticmethod
    def _mock_title(rng: random.Random, mood: str, genre: str) -> str:
        words_a = ["Midnight", "Neon", "Velvet", "Distant", "Paper", "Golden", "Quiet"]
        words_b = ["Tides", "Echoes", "Skyline", "Garden", "Signal", "Mirage", "Drift"]
        return f"{rng.choice(words_a)} {rng.choice(words_b)}"

    # --- gemini ---
    def _gemini_briefs(self, profile: TrendProfile, n: int) -> list[CreativeBrief]:
        import google.generativeai as genai

        genai.configure(api_key=self.settings.gemini_api_key)
        model = genai.GenerativeModel(
            self.settings.gemini_model, system_instruction=_BRIEF_SYSTEM_PROMPT
        )

        prompt = (
            f"Using ONLY this abstract trend profile:\n{json.dumps(profile.to_dict())}\n\n"
            f"Invent {n} wholly ORIGINAL song concepts. "
            "Return STRICT JSON: a list of objects with keys: "
            "title, genre, sub_genre, mood, bpm (int), musical_key, "
            "instruments (list[str]), structure (list[str] using section names like "
            "intro/verse/pre-chorus/chorus/bridge/outro), theme, is_instrumental (bool), "
            "vocal_type, production_notes, energy_arc, hook, "
            "lyrics (full original lyrics WITH SUNO section tags like [Verse]/[Chorus]; "
            "empty string if instrumental). "
            "Lyrics must be original and must not quote or paraphrase any real song."
        )
        resp = model.generate_content(prompt)
        items = _extract_json(resp.text)
        if isinstance(items, dict):
            items = items.get("songs") or items.get("items") or [items]

        briefs: list[CreativeBrief] = []
        for i, item in enumerate(items[:n]):
            rng = random.Random(f"{profile.captured_at}:gemini:{i}")
            instrumental = bool(item.get("is_instrumental", self._is_instrumental(i, n)))
            briefs.append(
                self._assemble_brief(
                    rng=rng,
                    title=item.get("title", f"Untitled {i + 1}"),
                    genre=item.get("genre", "Electronic"),
                    mood=item.get("mood", "chill"),
                    bpm=int(item.get("bpm", 100)),
                    key=item.get("musical_key", "C major"),
                    instruments=item.get("instruments", []),
                    structure=item.get("structure", ["intro", "verse", "chorus", "verse", "chorus", "outro"]),
                    theme=item.get("theme", ""),
                    instrumental=instrumental,
                    sub_genre=item.get("sub_genre", ""),
                    vocal_type=item.get("vocal_type", ""),
                    production_notes=item.get("production_notes", ""),
                    energy_arc=item.get("energy_arc", ""),
                    hook=item.get("hook", ""),
                    lyrics_body=item.get("lyrics") or item.get("suno_lyrics_prompt"),
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
