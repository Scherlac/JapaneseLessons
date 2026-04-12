"""Language configuration for the English → Japanese language pair."""

from __future__ import annotations

from jlesson.video import tts_engine

from ..curriculum import JAP_GRAMMAR_PROGRESSION
from ._base import FieldMap, LanguageConfig
from .config_eng import ENGLISH_LANGUAGE
from .config_jap import JAPANESE_LANGUAGE

ENG_JAP_CONFIG = LanguageConfig(
    code="eng-jap",
    display_name="English-Japanese",
    source=ENGLISH_LANGUAGE,
    target=JAPANESE_LANGUAGE,

    voices=tts_engine.VOICES,

    grammar_progression=tuple(JAP_GRAMMAR_PROGRESSION),
    vocab_dir="vocab",
    curriculum_file="curriculum/curriculum.json",

    field_map=FieldMap(source="source", target="target"),

)
