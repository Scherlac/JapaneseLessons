"""Language configuration for the Hungarian → English language pair."""

from __future__ import annotations

from jlesson.video import tts_engine

from dataclasses import replace as _replace

from ..curriculum import ENG_GRAMMAR_PROGRESSION
from ._base import FieldMap, LanguageConfig
from .config_eng import ENGLISH_LANGUAGE
from .config_hun import HUNGARIAN_LANGUAGE

HUN_ENG_CONFIG = LanguageConfig(
    code="hun-eng",
    display_name="Hungarian-English",
    source=HUNGARIAN_LANGUAGE,
    target=_replace(
        ENGLISH_LANGUAGE, 
        primary_voice="english_uk_female", 
        alternate_voice="english_uk_male"
    ),

    voices=tts_engine.VOICES,

    canonical_language="english",

    grammar_progression=tuple(ENG_GRAMMAR_PROGRESSION),
    vocab_dir="vocab/english",
    curriculum_file="curriculum/curriculum_english.json",

    field_map=FieldMap(source="source", target="target"),

)
