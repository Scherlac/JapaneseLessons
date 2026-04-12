"""Language configuration for the Hungarian → German language pair."""

from __future__ import annotations

from jlesson.video import tts_engine

from ..curriculum import GER_GRAMMAR_PROGRESSION
from ._base import FieldMap, LanguageConfig
from .config_hun import HUNGARIAN_LANGUAGE
from .config_ger import GERMAN_LANGUAGE

HUN_GER_CONFIG = LanguageConfig(
    code="hun-ger",
    display_name="Hungarian-German",
    source=HUNGARIAN_LANGUAGE,
    target=GERMAN_LANGUAGE,

    voices=tts_engine.VOICES,

    canonical_language="english",

    grammar_progression=tuple(GER_GRAMMAR_PROGRESSION),
    vocab_dir="vocab/german",
    curriculum_file="curriculum/curriculum_german.json",

    field_map=FieldMap(source="source", target="target"),

)
