"""SUNO 向けプロンプト生成（スタイル・歌詞）の品質チューニング層。

目的:
- SUNO が解釈しやすい構造化スタイル文字列を組み立てる。
- SUNO のセクションタグ（[Verse]/[Chorus] 等）付きの歌詞スキャフォールドを作る。
- Gemini 実モードとモックの双方で同じ語彙・構造を共有し、品質を底上げする。

著作権セーフ:
- いずれの出力にも「オリジナルであること」「実在の曲・アーティストを参照しない」
  というガードレールを含める。
"""

from __future__ import annotations

import random

# スタイル記述に使う抽象語彙（特定アーティスト/楽曲は一切含めない）
VOCAL_TYPES = [
    "warm female vocals",
    "smooth male vocals",
    "airy androgynous vocals",
    "soft duet harmonies",
    "intimate close-mic vocals",
]

PRODUCTION_DESCRIPTORS = [
    "wide stereo field",
    "lush reverb tails",
    "tape saturation warmth",
    "punchy sidechained dynamics",
    "crisp transient detail",
    "analog-leaning low end",
]

ENERGY_ARCS = [
    "slow build into a soaring chorus",
    "steady groove with a lifted bridge",
    "intimate verses opening into a wide hook",
    "pulsing momentum with a stripped breakdown",
]

GUARDRAIL = "original composition, do not imitate or reference any existing song or artist"

# SUNO が認識しやすいセクションタグ
SECTION_TAGS = {
    "intro": "[Intro]",
    "verse": "[Verse]",
    "verse1": "[Verse 1]",
    "verse2": "[Verse 2]",
    "prechorus": "[Pre-Chorus]",
    "chorus": "[Chorus]",
    "bridge": "[Bridge]",
    "drop": "[Drop]",
    "breakdown": "[Breakdown]",
    "outro": "[Outro]",
}


def build_style_prompt(
    *,
    genre: str,
    mood: str,
    bpm: int,
    musical_key: str,
    instruments: list[str],
    is_instrumental: bool,
    sub_genre: str = "",
    vocal_type: str = "",
    production_notes: str = "",
    energy_arc: str = "",
    rng: random.Random | None = None,
) -> str:
    """SUNO の style/tags 欄向けの構造化スタイル文字列を組み立てる。"""
    rng = rng or random.Random()
    parts: list[str] = []

    head = f"{mood} {genre}".strip()
    if sub_genre:
        head += f" / {sub_genre}"
    parts.append(head)

    parts.append(f"{bpm} BPM")
    if musical_key:
        parts.append(musical_key)

    if instruments:
        parts.append(", ".join(instruments[:5]))

    if is_instrumental:
        parts.append("instrumental, no vocals")
    else:
        parts.append(vocal_type or rng.choice(VOCAL_TYPES))

    parts.append(production_notes or rng.choice(PRODUCTION_DESCRIPTORS))
    parts.append(energy_arc or rng.choice(ENERGY_ARCS))
    parts.append(GUARDRAIL)

    return ", ".join(p for p in parts if p)


def normalize_structure(structure: list[str]) -> list[str]:
    """構成リストを SUNO セクションタグへ正規化する。"""
    tags: list[str] = []
    verse_n = 0
    for sec in structure or ["intro", "verse", "chorus", "verse", "chorus", "outro"]:
        key = sec.lower().replace(" ", "").replace("-", "")
        if key in ("verse", "verse1", "verse2"):
            verse_n += 1
            tags.append(f"[Verse {verse_n}]")
        else:
            tags.append(SECTION_TAGS.get(key, f"[{sec.title()}]"))
    return tags


def build_lyrics_scaffold(
    *,
    structure: list[str],
    mood: str,
    theme: str,
    hook: str = "",
    language: str = "English",
    rng: random.Random | None = None,
) -> str:
    """SUNO セクションタグ付きの歌詞スキャフォールドを生成する。

    モック用の安全なプレースホルダー本文を埋める（オリジナル・実在参照なし）。
    実モードでは Gemini が本文を生成し、この構造を踏襲させる。
    """
    rng = rng or random.Random()
    hook = hook or _placeholder_hook(mood, theme, language)
    lines: list[str] = []
    for tag in normalize_structure(structure):
        lines.append(tag)
        if tag.startswith("[Chorus]") or tag == "[Chorus]":
            lines.append(hook)
            lines.append(_placeholder_line(mood, theme, language, rng))
        elif tag.startswith("[Drop]") or tag.startswith("[Breakdown]"):
            lines.append("(instrumental)")
        else:
            lines.append(_placeholder_line(mood, theme, language, rng))
            lines.append(_placeholder_line(mood, theme, language, rng))
        lines.append("")
    return "\n".join(lines).strip() + "\n"


# --- プレースホルダー本文（オリジナル・実在参照なし）---

_EN_IMAGES = [
    "city lights blur into the rain",
    "we trace the quiet of the dawn",
    "a softer signal in the noise",
    "holding still while the world turns on",
    "every echo finds its way back home",
]
_JA_IMAGES = [
    "夜更けの灯りがにじむ",
    "静かな朝をなぞる",
    "ノイズの中の小さな合図",
    "世界が回る間そっと佇む",
    "響きはいつか帰り着く",
]


def _placeholder_line(mood: str, theme: str, language: str, rng: random.Random) -> str:
    pool = _JA_IMAGES if language.lower().startswith("japan") else _EN_IMAGES
    return rng.choice(pool)


def _placeholder_hook(mood: str, theme: str, language: str) -> str:
    if language.lower().startswith("japan"):
        return f"この{mood}な夜に、オリジナルのメロディを"
    return f"an original {mood} hook that lifts the night"
