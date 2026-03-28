"""Language configuration for the English → Japanese language pair."""

from __future__ import annotations

from jlesson.video import tts_engine

from ..curriculum import ENG_TO_JAP_GRAMMAR_PROGRESSION
from ..item_generator import EngJapItemGenerator
from ..prompt_template import EngJapPrompts, PERSONS_BEGINNER
from ._base import FieldMap, LanguageConfig
from ._partials import ENGLISH_LANGUAGE, JAPANESE_LANGUAGE

ENG_JAP_CONFIG = LanguageConfig(
    code="eng-jap",
    display_name="English-Japanese",
    source=ENGLISH_LANGUAGE,
    target=JAPANESE_LANGUAGE,

    voices=tts_engine.VOICES,

    grammar_progression=tuple(ENG_TO_JAP_GRAMMAR_PROGRESSION),
    persons=tuple(PERSONS_BEGINNER),

    vocab_dir="vocab",
    curriculum_file="curriculum/curriculum.json",

    field_map=FieldMap(source="source", target="target"),

    generator=EngJapItemGenerator(),
    prompts=EngJapPrompts(),
)
