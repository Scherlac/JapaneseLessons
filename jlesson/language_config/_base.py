"""
Core language configuration types and registry.

Defines the FieldMap, PartialLanguageConfig, and LanguageConfig dataclasses
used by language-specific and language-pair configuration modules, plus the
global registry and lookup function.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from ..models import GrammarItem
from ..item_generator import ItemGenerator
from ..prompt_template import PromptInterface


@dataclass
class FieldMap:
    """Maps generic semantic roles to source/target roots on a lesson item.

    Language-local field paths such as pronunciation, example sentence, or
    target-side special fields belong on ``PartialLanguageConfig``. ``FieldMap``
    only defines where the source and target objects live on the model being
    viewed.

    Role semantics
    --------------
    source
        Root path for the learner's native-language object.
        e.g. ``"source"`` for ``GeneralItem`` or ``"english"`` for a flat dict.
    target
        Root path for the language-being-learned object.
        e.g. ``"target"`` for ``GeneralItem`` or ``"japanese"`` for a flat dict.
    """

    source: str
    target: str

    def view(
        self,
        item: Any,
        source_fields: PartialFieldMap | None = None,
        target_fields: PartialFieldMap | None = None,
    ) -> dict[str, Any]:
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

        def _resolve(root: str, relative_path: str) -> str:
            if not root or not relative_path:
                return ""
            return _get(f"{root}.{relative_path}")

        source_fields = source_fields or PartialFieldMap(text_path="")
        target_fields = target_fields or PartialFieldMap(text_path="")

        return {
            "source": _resolve(self.source, source_fields.text_path),
            "target": _resolve(self.target, target_fields.text_path),
            "target_phonetic": _resolve(self.target, target_fields.phonetic_path),
            "target_special": {
                role: _resolve(self.target, fname) for role, fname in target_fields.special_paths.items()
            },
            "example_sentence_source": _resolve(self.source, source_fields.example_sentence_path),
            "example_sentence_target": _resolve(self.target, target_fields.example_sentence_path),
        }


@dataclass(frozen=True)
class PartialFieldMap:
    """Language-local field mapping relative to a source or target root."""

    text_path: str = "display_text"
    phonetic_path: str = ""
    example_sentence_path: str = ""
    special_paths: dict[str, str] = field(default_factory=dict)
    special_labels: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class PartialLanguageConfig:
    """Immutable configuration shared by both source and target languages.

    This type holds per-language facts only. Direction-specific behavior stays
    on the pair-level LanguageConfig.
    """

    code: str
    display_name: str
    field_map: PartialFieldMap = field(default_factory=PartialFieldMap)
    label: str = ""
    phonetic_label: str = ""
    font_path: str = ""
    noun_fields: frozenset[str] = field(default_factory=frozenset)
    verb_fields: frozenset[str] = field(default_factory=frozenset)
    verb_types: frozenset[str] = field(default_factory=frozenset)
    adj_fields: frozenset[str] = field(default_factory=frozenset)
    adj_types: frozenset[str] = field(default_factory=frozenset)
    primary_voice: str = ""
    alternate_voice: str = ""
    extra_display_keys: tuple[str, ...] = ()
    card_extra_font_keys: dict[str, str] = field(default_factory=dict)
    vocab_source_key: str = ""
    vocab_phonetic_key: str = ""


@dataclass(frozen=True)
class LanguageConfig:
    """Immutable bundle of every setting that varies between language pairs."""

    # ── Identity ──────────────────────────────────────────────────────────
    code: str
    display_name: str
    canonical_language: str = "english"  # for prompt builders that need a single language
    source: PartialLanguageConfig
    target: PartialLanguageConfig

    # ── TTS voices ────────────────────────────────────────────────────────
    voices: dict[str, str]

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

    @property
    def native_language(self) -> str:
        """Backward-compatible alias for the learner's source language."""
        return self.source.display_name

    @property
    def target_language(self) -> str:
        """Backward-compatible alias for the lesson target language."""
        return self.target.display_name

    @property
    def native_font_path(self) -> str:
        """Backward-compatible alias for the source language font path."""
        return self.source.font_path

    @property
    def target_font_path(self) -> str:
        """Backward-compatible alias for the target language font path."""
        return self.target.font_path

    @property
    def vocab_noun_fields(self) -> frozenset[str]:
        """Combined noun schema used by current vocab validation code."""
        return self.source.noun_fields | self.target.noun_fields

    @property
    def vocab_verb_fields(self) -> frozenset[str]:
        """Combined verb schema used by current vocab validation code."""
        return self.source.verb_fields | self.target.verb_fields

    @property
    def vocab_verb_types(self) -> frozenset[str]:
        """Combined verb type set kept for backward compatibility."""
        return self.source.verb_types | self.target.verb_types

    @property
    def vocab_adj_fields(self) -> frozenset[str]:
        """Combined adjective schema used by current vocab validation code."""
        return self.source.adj_fields | self.target.adj_fields

    @property
    def vocab_adj_types(self) -> frozenset[str]:
        """Combined adjective type set kept for backward compatibility."""
        return self.source.adj_types | self.target.adj_types

    @property
    def source_label(self) -> str:
        """Preferred source label for reports and rendering."""
        return self.source.label

    @property
    def target_label(self) -> str:
        """Preferred target label for reports and rendering."""
        return self.target.label

    @property
    def phonetic_label(self) -> str:
        """Preferred phonetic label for reports and rendering."""
        return self.target.phonetic_label

    @property
    def source_voice(self) -> str:
        """Voice used for source-language audio assets."""
        return self.source.primary_voice

    @property
    def target_voice_female(self) -> str:
        """Primary target-language voice used for audio assets."""
        return self.target.primary_voice

    @property
    def target_voice_male(self) -> str:
        """Alternate target-language voice used for audio assets."""
        return self.target.alternate_voice or self.target.primary_voice

    @property
    def target_extra_display_keys(self) -> list[str]:
        """Ordered target extra keys to show on cards."""
        return list(self.target.extra_display_keys)

    @property
    def target_card_extra_font_keys(self) -> dict[str, str]:
        """Font selection for target extras rendered on cards."""
        return dict(self.target.card_extra_font_keys)

    @property
    def target_special_paths(self) -> dict[str, str]:
        """Target-only extra fields exposed by the lesson data model."""
        return dict(self.target.field_map.special_paths)

    @property
    def target_special_labels(self) -> dict[str, str]:
        """Display labels for target-special fields (role -> label)."""
        return dict(self.target.field_map.special_labels)

    def view(self, item: Any) -> dict[str, Any]:
        """Return a generic role-based view of *item* using split role config."""
        view = self.field_map.view(item, self.source.field_map, self.target.field_map)
        view["source_label"] = self.source_label
        view["target_label"] = self.target_label
        view["phonetic_label"] = self.phonetic_label
        return view


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
