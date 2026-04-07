"""Language configuration for the English → French language pair."""

from __future__ import annotations

from jlesson.video import tts_engine

from ..curriculum import ENG_TO_FRE_GRAMMAR_PROGRESSION
from ..item_generator import EngFrItemGenerator
from ..prompt_template import EngFrPrompts, FRENCH_PERSONS
from ._base import FieldMap, LanguageConfig
from ._partials import ENGLISH_LANGUAGE, FRENCH_LANGUAGE

ENG_FRE_CONFIG = LanguageConfig(
    code="eng-fre",
    display_name="English-French",
    source=ENGLISH_LANGUAGE,
    target=FRENCH_LANGUAGE,

    voices=tts_engine.VOICES,

    canonical_language="english",

    grammar_progression=tuple(ENG_TO_FRE_GRAMMAR_PROGRESSION),
    persons=tuple(FRENCH_PERSONS),

    vocab_dir="vocab/french",
    curriculum_file="curriculum/curriculum_french.json",

    field_map=FieldMap(source="source", target="target"),

    generator=EngFrItemGenerator(),
    prompts=EngFrPrompts(),
)
