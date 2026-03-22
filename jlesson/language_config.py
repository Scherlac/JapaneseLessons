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

from typing import Any, Optional

from dataclasses import dataclass, field
from typing import Any

from jlesson.video import tts_engine
from jlesson.item_generator import ItemGenerator


@dataclass
class FieldMap:
    """Maps generic semantic role names to language-specific model field names.

    The mapping is used by pipeline stages (report builder, asset compiler,
    card renderer) so they can operate on ``source``/``target`` roles instead
    of hard-coding language-specific field names such as ``japanese`` or
    ``hungarian``.

    Role semantics
    --------------
    source
        The learner's *native* language text — the prompt side of a flash card.
        e.g. ``"english"`` for eng-jap, ``"hungarian"`` for hun-eng.
    target
        The *language being learned* — the reveal side of a flash card.
        e.g. ``"japanese"`` for eng-jap, ``"english"`` for hun-eng.
    target_phonetic
        A phonetic / romanisation field for the target text (may be empty).
        e.g. ``"romaji"`` for eng-jap, ``"pronunciation"`` (IPA) for hun-eng.
    target_special
        Additional named fields for the target language, accessed by role.
        e.g. ``{"kanji": "kanji", "masu_form": "masu_form"}`` for eng-jap.
    example_sentence_source / example_sentence_target
        Field names for example sentences in source / target language.
    source_label / target_label / phonetic_label
        Human-readable display names used by the report builder.
    """

    source: str
    target: str
    target_phonetic: str = ""
    target_special: dict[str, str] = field(default_factory=dict)
    example_sentence_source: str = ""
    example_sentence_target: str = ""
    source_label: str = ""
    target_label: str = ""
    phonetic_label: str = ""
    # Voice key names (must match keys in LanguageConfig.voices)
    source_voice: str = "english_female"      # audio_src asset
    target_voice_female: str = "japanese_female"  # audio_tar_f asset
    target_voice_male: str = "japanese_male"      # audio_tar_m asset
    # Card rendering — target block layout
    # extra_display_keys: ordered list of item.target.extra keys to show on cards.
    #   Leave empty to show all extras in dict order.
    # card_extra_font_keys: per-extra-key font mapping  {extra_key: font_key}.
    #   font_key must match a key in CardRenderer.fonts.
    #   If a key is absent, falls back to "en_small".
    extra_display_keys: list = field(default_factory=list)
    card_extra_font_keys: dict = field(default_factory=dict)

    def view(self, item: Any) -> dict[str, Any]:
        """Return a generic-keyed dict extracted from *item*.

        *item* may be a Pydantic model (extra fields accessible via
        ``model_extra``) or a plain :class:`dict`.  Unknown field names
        silently resolve to ``""`` so callers never get ``KeyError``.
        """

        def _get(field_name: str) -> str:
            if not field_name:
                return ""
            # Handle dotted paths for both dict and objects
            parts = field_name.split(".")
            obj = item
            for part in parts:
                if isinstance(obj, dict):
                    obj = obj.get(part)
                elif hasattr(obj, part):
                    obj = getattr(obj, part)
                else:
                    return ""
                if obj is None:
                    return ""
            return obj or ""

        return {
            "source": _get(self.source),
            "target": _get(self.target),
            "target_phonetic": _get(self.target_phonetic),
            "target_special": {
                role: _get(fname) for role, fname in self.target_special.items()
            },
            "example_sentence_source": _get(self.example_sentence_source),
            "example_sentence_target": _get(self.example_sentence_target),
            "source_label": self.source_label,
            "target_label": self.target_label,
            "phonetic_label": self.phonetic_label,
        }


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
    grammar_progression: tuple[GrammarItem, ...] = ()
    persons: tuple[tuple[str, str, str], ...] = ()

    # ── File-system layout ────────────────────────────────────────────────
    vocab_dir: str = "vocab"
    curriculum_file: str = "curriculum/curriculum.json"

    # ── Field role mapping ────────────────────────────────────────────────
    field_map: FieldMap = field(default_factory=lambda: FieldMap(source="", target=""))

    # ── Item generator ────────────────────────────────────────────────────
    generator: Optional[ItemGenerator] = None

    # ── Prompt builders ───────────────────────────────────────────────────
    prompts: Optional[PromptInterface] = None


# ── Pre-built configs ─────────────────────────────────────────────────────────
# Values are read from the existing codebase — not guessed.
# Sources: models.py, vocab_generator.py, tts_engine.py, cards.py,
#          curriculum.py, prompt_template.py

# Lazy imports to avoid circular dependencies and keep source modules unchanged.
from .curriculum import (  # noqa: E402
    ENG_TO_JAP_GRAMMAR_PROGRESSION,
    HUN_TO_ENG_GRAMMAR_PROGRESSION,
)
from .models import GrammarItem  # noqa: E402
from .prompt_template import EngJapPrompts, HunEngPrompts, PromptInterface, PERSONS_BEGINNER, HUNGARIAN_PERSONS
from .item_generator import EngJapItemGenerator, HunEngItemGenerator  # noqa: E402

ENG_JAP_CONFIG = LanguageConfig(
    code="eng-jap",
    display_name="English-Japanese",
    target_language="Japanese",
    native_language="English",

    vocab_noun_fields=frozenset({"english", "japanese", "kanji", "romaji"}),
    vocab_verb_fields=frozenset({"english", "japanese", "kanji", "romaji", "type", "masu_form"}),
    vocab_verb_types=frozenset({"る-verb", "う-verb", "irregular", "な-adj"}),

    voices=tts_engine.VOICES,

    target_font_path="C:/Windows/Fonts/YuGothB.ttc",
    native_font_path="C:/Windows/Fonts/segoeui.ttf",

    grammar_progression=tuple(ENG_TO_JAP_GRAMMAR_PROGRESSION),
    persons=tuple(PERSONS_BEGINNER),

    vocab_dir="vocab",
    curriculum_file="curriculum/curriculum.json",

    field_map=FieldMap(
        source="source.display_text",
        target="target.display_text",
        target_phonetic="target.pronunciation",
        target_special={"kanji": "target.kanji", "masu_form": "target.masu_form"},
        example_sentence_source="source.extra.example_sentence_en",
        example_sentence_target="target.extra.example_sentence_jp",
        source_label="English",
        target_label="Japanese",
        phonetic_label="Romaji",
        source_voice="english_female",
        target_voice_female="japanese_female",
        target_voice_male="japanese_male",
        # Show kana then masu-form under the main Japanese text on cards.
        # kana and masu_form are Japanese script → use jp_small
        extra_display_keys=["kana", "masu_form"],
        card_extra_font_keys={"kana": "jp_small", "masu_form": "jp_small"},
    ),

    generator=EngJapItemGenerator(),

    prompts=EngJapPrompts(),
)

HUN_ENG_CONFIG = LanguageConfig(
    code="hun-eng",
    display_name="Hungarian-English",
    target_language="English",
    native_language="Hungarian",

    vocab_noun_fields=frozenset({"english", "hungarian", "pronunciation"}),
    vocab_verb_fields=frozenset({"english", "hungarian", "pronunciation", "past_tense"}),
    vocab_verb_types=frozenset(),  # English verbs don't use Japanese-style type classes

    voices=tts_engine.VOICES,

    target_font_path="C:/Windows/Fonts/segoeui.ttf",
    native_font_path="C:/Windows/Fonts/segoeui.ttf",

    grammar_progression=tuple(HUN_TO_ENG_GRAMMAR_PROGRESSION),
    persons=tuple(HUNGARIAN_PERSONS),

    vocab_dir="vocab/hungarian",
    curriculum_file="curriculum/curriculum_hungarian.json",

    field_map=FieldMap(
        source="source.display_text",
        target="target.display_text",
        target_phonetic="target.pronunciation",
        target_special={},
        example_sentence_source="source.extra.example_sentence_hu",
        example_sentence_target="target.extra.example_sentence_en",
        source_label="Magyar",
        target_label="English",
        phonetic_label="Pronunciation",
        source_voice="hungarian_female",
        target_voice_female="english_uk_female",
        target_voice_male="english_uk_male",
        # Pronunciation already in target.pronunciation; no extra fields needed.
        # No extra display keys for hun-eng; pronunciation is already shown
        extra_display_keys=[],
        card_extra_font_keys={},
    ),

    generator=HunEngItemGenerator(),

    prompts=HunEngPrompts(),
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
