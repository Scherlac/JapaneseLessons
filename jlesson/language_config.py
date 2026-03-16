"""
Language configuration module — central registry of language-specific settings.

Each language pair (native → target) is described by a LanguageConfig dataclass
that captures vocabulary schema, TTS voices, font paths, grammar progression,
and file-system layout.  All language-specific decisions are made here so the
rest of the pipeline can remain language-agnostic.

Code convention — the ``code`` field uses **native-target** format:
    eng-jap  →  English speaker learning Japanese
    hun-eng  →  Hungarian speaker learning English

Usage:
    from jlesson.language_config import get_language_config
    cfg = get_language_config("eng-jap")
    print(cfg.display_name)  # "English-Japanese"
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class LanguageConfig:
    """Immutable bundle of every setting that varies between language pairs."""

    # ── Identity ──────────────────────────────────────────────────────────
    code: str
    display_name: str
    target_language: str
    native_language: str

    # ── Vocabulary schema ─────────────────────────────────────────────────
    vocab_noun_fields: frozenset[str]
    vocab_verb_fields: frozenset[str]
    vocab_verb_types: frozenset[str]

    # ── TTS voices ────────────────────────────────────────────────────────
    voices: dict[str, str]

    # ── Font paths (Windows, see TD-05 for cross-platform) ───────────────
    target_font_path: str
    native_font_path: str

    # ── Grammar & persons (may be populated later) ────────────────────────
    grammar_progression: tuple[dict, ...] = ()
    persons: tuple[tuple[str, str, str], ...] = ()

    # ── File-system layout ────────────────────────────────────────────────
    vocab_dir: str = "vocab"
    curriculum_file: str = "curriculum/curriculum.json"


# ── Pre-built configs ─────────────────────────────────────────────────────────
# Values are read from the existing codebase — not guessed.
# Sources: models.py, vocab_generator.py, tts_engine.py, cards.py,
#          curriculum.py, prompt_template.py

# Lazy imports to avoid circular dependencies and keep source modules unchanged.
from .curriculum import (  # noqa: E402
    ENG_TO_JAP_GRAMMAR_PROGRESSION,
    HUN_TO_ENG_GRAMMAR_PROGRESSION,
)
from .prompt_template import PERSONS_BEGINNER  # noqa: E402
from .prompt_template import HUNGARIAN_PERSONS  # noqa: E402

ENG_JAP_CONFIG = LanguageConfig(
    code="eng-jap",
    display_name="English-Japanese",
    target_language="Japanese",
    native_language="English",

    vocab_noun_fields=frozenset({"english", "japanese", "kanji", "romaji"}),
    vocab_verb_fields=frozenset({"english", "japanese", "kanji", "romaji", "type", "masu_form"}),
    vocab_verb_types=frozenset({"る-verb", "う-verb", "irregular", "な-adj"}),

    voices={
        "japanese_female": "ja-JP-NanamiNeural",
        "japanese_male": "ja-JP-KeitaNeural",
        "english_female": "en-US-AriaNeural",
        "english_male": "en-US-ZiraNeural",
    },

    target_font_path="C:/Windows/Fonts/YuGothB.ttc",
    native_font_path="C:/Windows/Fonts/segoeui.ttf",

    grammar_progression=tuple(ENG_TO_JAP_GRAMMAR_PROGRESSION),
    persons=tuple(PERSONS_BEGINNER),

    vocab_dir="vocab",
    curriculum_file="curriculum/curriculum.json",
)

HUN_ENG_CONFIG = LanguageConfig(
    code="hun-eng",
    display_name="Hungarian-English",
    target_language="English",
    native_language="Hungarian",

    vocab_noun_fields=frozenset({"english", "hungarian", "pronunciation"}),
    vocab_verb_fields=frozenset({"english", "hungarian", "pronunciation", "past_tense"}),
    vocab_verb_types=frozenset(),  # English verbs don't use Japanese-style type classes

    voices={
        "hungarian_female": "hu-HU-NoemiNeural",
        "hungarian_male": "hu-HU-TamasNeural",
        "english_female": "en-US-AriaNeural",
        "english_male": "en-US-ZiraNeural",
    },

    target_font_path="C:/Windows/Fonts/segoeui.ttf",
    native_font_path="C:/Windows/Fonts/segoeui.ttf",

    grammar_progression=tuple(HUN_TO_ENG_GRAMMAR_PROGRESSION),
    persons=tuple(HUNGARIAN_PERSONS),

    vocab_dir="vocab/hungarian",
    curriculum_file="curriculum/curriculum_hungarian.json",
)

# ── Registry ──────────────────────────────────────────────────────────────────

_CONFIGS: dict[str, LanguageConfig] = {
    ENG_JAP_CONFIG.code: ENG_JAP_CONFIG,
    HUN_ENG_CONFIG.code: HUN_ENG_CONFIG,
}


def get_language_config(code: str) -> LanguageConfig:
    """Return the LanguageConfig for a language-pair code.

    Args:
        code: Language-pair identifier, e.g. ``'eng-jap'`` or ``'hun-eng'``.

    Raises:
        ValueError: If the code is not registered.
    """
    cfg = _CONFIGS.get(code)
    if cfg is None:
        valid = ", ".join(sorted(_CONFIGS))
        raise ValueError(
            f"Unknown language code {code!r}. Valid codes: {valid}"
        )
    return cfg
