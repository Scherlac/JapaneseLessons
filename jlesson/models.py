"""
Pydantic data models for Japanese lesson content.

These schemas define the shapes of LLM-generated data used across the pipeline
and serialised to output/<lesson_id>/content.json by lesson_store.py.

Compilation pipeline models (GeneralItem, Touch) define the data shapes for
the three-stage transformation: item_sequence → compiled_items → touch_sequence.
"""

from __future__ import annotations

from enum import Enum
import hashlib
from random import random, sample
import re

from pathlib import Path
from typing import Any, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Phase(str, Enum):
    """Lesson phase — determines which repetition cycle applies."""

    UNKNOWN = "unknown"
    NOUNS = "nouns"
    VERBS = "verbs"
    ADJECTIVES = "adjectives"
    VOCAB = "vocab"  # general catch-all for words that don't fit neatly into noun/verb/adjective categories
    GRAMMAR = "grammar" # grammar points and practice sentences
    NARRATIVE = "narrative" # narrative story blocks making lesson cohesive and memorable


class _NullStrCoerce(BaseModel):
    """Mixin: convert any None value for a field declared as str to ''.

    Handles LLMs that return ``null`` for optional-feeling string fields
    (e.g. ``notes``, ``memory_tip``) instead of omitting them or using ``""``.
    """

    @model_validator(mode="before")
    @classmethod
    def _coerce_null_strings(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data
        annotations = {}
        for klass in reversed(cls.__mro__):
            annotations.update(getattr(klass, "__annotations__", {}))
        for field, annotation in annotations.items():
            if annotation is str and data.get(field) is None:
                data[field] = ""
        return data


class PartialItem(BaseModel):

    display_text: str = ""
    tts_text: str = ""
    pronunciation: str = ""
    extra: dict[str, Any] = Field(default_factory=dict)
    assets: dict[str, Path] = Field(default_factory=dict)


class CanonicalItem(BaseModel):
    """Meaning-stable canonical representation of a lesson vocabulary term.

    Language-neutral.  Source of truth for retrieval, embeddings, and
    cross-language branch attachment.  ``text`` is the canonical English
    word or phrase; ``gloss`` disambiguates when the same surface form has
    multiple senses; ``context`` anchors meaning to the narrative passage
    the term came from.
    """

    id: str = ""
    embeddings: list[float] = Field(default_factory=list,
        description=( 
            """LLM-generated vector embeddings for this item, used for retrieval and inter-step 
            reference resolution.  Populated in the item generation step and consumed in later 
            steps like lesson planning and touch compilation."""))
    text: str = Field(default="", description="The canonical English word or phrase representing the core meaning of this item.")
    type: Phase = Field(default=Phase.UNKNOWN, description="The lesson phase this item belongs to (e.g. noun, verb, grammar, etc.)")
    gloss: str = Field(default="", 
        description=(
            """A brief gloss to disambiguate the meaning when the same surface form has multiple 
            senses, e.g. 'bank (river)' vs. 'bank (finance)'."""))
    
    SLUG_FILTER_REGEX: str = r'[^\w]+'
    COMPILED_SLUG_FILTER_REGEX = re.compile(SLUG_FILTER_REGEX)

    @staticmethod
    def update_item(item: CanonicalItem, phase: Phase) -> None:
        """Update the item's type and id based on its text, gloss, and phase."""
        # Generate a stable ID based on the text, gloss, and phase
        item.type = phase
        
        slug_text = CanonicalItem.COMPILED_SLUG_FILTER_REGEX.sub("_", item.text.lower().strip())
        slug_gloss = CanonicalItem.COMPILED_SLUG_FILTER_REGEX.sub("_", item.gloss.lower().strip())
        hash_input = f"{phase.value}_{slug_text}_{slug_gloss}"

        gloss_hash = hashlib.sha1(hash_input.encode()).hexdigest()

        slug_text_parts = slug_text.split("_")
        if len(slug_text_parts) > 4:
            short_slug_text = "_".join(slug_text_parts[:3] + slug_text_parts[-1:])
        else:
            short_slug_text = slug_text

        item.id = f"{phase.value}_{short_slug_text}_{gloss_hash[:6]}"


class GeneralItem(_NullStrCoerce):
    """A general lesson item with flexible fields for any language pair.

    This is used as an intermediate type for LLM responses before validation
    and transformation into the more specific GeneralItem / GeneralItem / Sentence
    models.  It allows the LLM to return extra fields without causing parsing
    errors, which is useful for accommodating different language pairs with
    varying requirements.
    """
    id: str = ""
    canonical: CanonicalItem = Field(default_factory=CanonicalItem)
    source: PartialItem = Field(default_factory=PartialItem)
    target: PartialItem = Field(default_factory=PartialItem)
    assets: dict[str, Path] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional arbitrary metadata from the LLM, preserved for flexibility.")
    block_index: int = 1
    phase: Phase | None = None

    @model_validator(mode="before")
    @classmethod
    def _coerce_legacy_item_type(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data
        if data.get("phase"):
            return data
        legacy_item_type = data.get("item_type")
        legacy_phase_map = {
            "noun": "nouns",
            "verb": "verbs",
            "sentence": "grammar",
        }
        if isinstance(legacy_item_type, str):
            legacy_phase = legacy_phase_map.get(legacy_item_type.strip().lower())
            if legacy_phase:
                data["phase"] = legacy_phase
        return data



class Sentence(GeneralItem):
    """A grammar practice sentence generated by the LLM.

    Extra fields (e.g. ``hungarian`` for hun-eng lessons) are preserved
    transparently in serialization so all language pairs round-trip correctly.
    """

    grammar_id: str = ""
    grammar_parameters: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _coerce_grammar_parameters(cls, data: object) -> object:
        """Coerce None values in grammar_parameters to empty strings.

        Some LLM responses may include nulls for optional parameters; this
        prevents Pydantic validation errors while keeping the dictionary
        structure intact.
        """
        if not isinstance(data, dict):
            return data
        gp = data.get("grammar_parameters")
        if isinstance(gp, dict):
            data["grammar_parameters"] = {
                k: (v if v is not None else "") for k, v in gp.items()
            }
        return data



class GrammarItem(BaseModel):
    """A grammar progression item with generalized fields.

    Used for both eng-jap and hun-eng grammar progressions.
    """
    id: str
    pattern: str
    description: str
    example_source: str
    example_target: str
    requires: list[str] = Field(default_factory=list)
    level: int = 1


class LessonContent(BaseModel):
    """Full structured content for one lesson — persisted to content.json."""

    lesson_id: int
    theme: str
    language: str = "eng-jap"
    narrative_blocks: list[str] = Field(default_factory=list)
    grammar_ids: list[str] = Field(default_factory=list)
    words: list[GeneralItem] = Field(default_factory=list)
    sentences: list[Sentence] = Field(default_factory=list)
    created_at: str = ""
    # Pipeline execution metadata
    pipeline_started_at: str = ""
    completed_steps: list[str] = Field(default_factory=list)
    step_timings: dict[str, float] = Field(default_factory=dict)
    # Per-step detail records: {step_name: {index, description, started_at, elapsed_s, status}}
    step_details: dict[str, dict] = Field(default_factory=dict)

    @property
    def noun_items(self) -> list[GeneralItem]:
        """Nouns from the words list."""
        return [w for w in self.words if w.phase == Phase.NOUNS]

    @property
    def verb_items(self) -> list[GeneralItem]:
        """Verbs from the words list."""
        return [w for w in self.words if w.phase == Phase.VERBS]


# ---------------------------------------------------------------------------
# Compilation pipeline models (Stages 2–3)
# ---------------------------------------------------------------------------


class TouchType(str, Enum):
    """Mechanical specification of a single touch interaction."""

    # Card-based (visual prompt → visual reveal)
    SOURCE_TARGET = "source→target"
    TARGET_SOURCE = "target→source"
    SOURCE_ONLY = "source only"
    TARGET_ONLY = "target only"

    # Listen-first (audio-led, passive-friendly)
    LISTEN_DUAL_M = "listen dual (s:m;t:f/m)" # source male voice, target: female, male voice
    LISTEN_DUAL_F = "listen dual (s:f;t:m/f)" # source female voice, target: male, female voice
    LISTEN_REVERSE_M = "listen reverse (t:m;s:m)" # target male voice, source male voice
    LISTEN_REVERSE_F = "listen reverse (t:f;s:f)" # target female voice, source female voice
    LISTEN_TARGET_M =    "listen target only (t:m)" # target male voice only
    LISTEN_TARGET_F =    "listen target only (t:f)" # target female voice only


class TouchIntent(str, Enum):
    """Pedagogical intent of a touch within a repetition cycle."""

    INTRODUCE = "introduce"
    RECALL = "recall"
    REINFORCE = "reinforce"
    CONFIRM = "confirm"
    LOCK_IN = "lock-in"
    TRANSLATE = "translate"
    COMPREHEND = "comprehend"
    UNKNOWN = "---"

    def show_source(self) -> bool:
        return self in [
            TouchIntent.INTRODUCE, 
            TouchIntent.RECALL,
            TouchIntent.REINFORCE,
            TouchIntent.CONFIRM,
            TouchIntent.COMPREHEND,
            TouchIntent.UNKNOWN,
        ]
    
    def show_target(self) -> bool:
        return self in [
            TouchIntent.INTRODUCE, 
            TouchIntent.RECALL, 
            TouchIntent.TRANSLATE, 
            TouchIntent.CONFIRM,
            TouchIntent.UNKNOWN,
        ]


class RepetitionStep(BaseModel):
    """One step in a repetition cycle: a touch type paired with its intent."""

    touch_type: TouchType
    intent: TouchIntent


LessonItem = Union[GeneralItem, GeneralItem, Sentence]


class Touch(BaseModel):
    """One learner interaction — output of Stage 3 (touch compiler).

    References a GeneralItem and specifies which assets to use.
    """
    touch_index: int
    phase: Phase

    item: GeneralItem = Field(default_factory=GeneralItem)
    touch_type: TouchType
    intent: TouchIntent

    artifacts: dict[str, Path | list[Path]] = Field(default_factory=dict)

    model_config = {"arbitrary_types_allowed": True}
