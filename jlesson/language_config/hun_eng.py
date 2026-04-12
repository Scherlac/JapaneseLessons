"""Language configuration for the Hungarian → English language pair."""

from __future__ import annotations

from jlesson.video import tts_engine

from ..curriculum import ENG_GRAMMAR_PROGRESSION
from ._base import FieldMap, LanguageConfig, PartialFieldMap, PartialLanguageConfig
from .config_eng import ENGLISH_LANGUAGE
from .config_hun import HUNGARIAN_LANGUAGE

HUN_ENG_CONFIG = LanguageConfig(
    code="hun-eng",
    display_name="Hungarian-English",
    source=HUNGARIAN_LANGUAGE,
    target=PartialLanguageConfig(
        code=ENGLISH_LANGUAGE.code,
        display_name=ENGLISH_LANGUAGE.display_name,
        field_map=PartialFieldMap(
            text_path="display_text",
            phonetic_path="pronunciation",
            example_sentence_path="extra.example_sentence_en",
        ),
        label=ENGLISH_LANGUAGE.label,
        phonetic_label=ENGLISH_LANGUAGE.phonetic_label,
        font_path=ENGLISH_LANGUAGE.font_path,
        noun_fields=frozenset({"english", "pronunciation"}),
        verb_fields=frozenset({"english", "pronunciation", "past_tense"}),
        adj_fields=frozenset({"english", "pronunciation"}),
        primary_voice="english_uk_female",
        alternate_voice="english_uk_male",
        extra_display_keys=ENGLISH_LANGUAGE.extra_display_keys,
        card_extra_font_keys=dict(ENGLISH_LANGUAGE.card_extra_font_keys),
        vocab_source_key="english",
        vocab_phonetic_key="pronunciation",
    ),

    voices=tts_engine.VOICES,

    grammar_progression=tuple(ENG_GRAMMAR_PROGRESSION),

    vocab_dir="vocab/hungarian",
    curriculum_file="curriculum/curriculum_hungarian.json",

    field_map=FieldMap(source="source", target="target"),


)
