"""Language configuration for the English → French language pair."""

from __future__ import annotations

from jlesson.video import tts_engine

from ..curriculum import FRE_GRAMMAR_PROGRESSION
from ._base import FieldMap, LanguageConfig
from .config_eng import ENGLISH_LANGUAGE
from .config_fre import FRENCH_LANGUAGE

ENG_FRE_CONFIG = LanguageConfig(
    code="eng-fre",
    display_name="English-French",
    source=ENGLISH_LANGUAGE,
    target=FRENCH_LANGUAGE,

    voices=tts_engine.VOICES,

    canonical_language="english",

    grammar_progression=tuple(FRE_GRAMMAR_PROGRESSION),
    vocab_dir="vocab/french",
    curriculum_file="curriculum/curriculum_french.json",

    field_map=FieldMap(source="source", target="target"),

)
