"""
Core language configuration types and registry.

Defines the FieldMap and LanguageConfig dataclasses that every language-pair
config must instantiate, plus the global registry and lookup function.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from ..models import GrammarItem
from ..item_generator import ItemGenerator
from ..prompt_template import PromptInterface


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
    source_voice: str = "english_female"          # audio_src asset
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


# ── Registry ──────────────────────────────────────────────────────────────────

_CONFIGS: dict[str, LanguageConfig] = {}


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
