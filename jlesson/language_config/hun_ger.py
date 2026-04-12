"""Language configuration for the Hungarian → German language pair."""

from __future__ import annotations

from jlesson.video import tts_engine

from ..curriculum import HUN_TO_GER_GRAMMAR_PROGRESSION
from ._base import FieldMap, LanguageConfig, PartialFieldMap, PartialLanguageConfig
from ._partials import GERMAN_LANGUAGE, HUNGARIAN_LANGUAGE

HUN_GER_CONFIG = LanguageConfig(
    code="hun-ger",
    display_name="Hungarian-German",
    source=HUNGARIAN_LANGUAGE,
    target=PartialLanguageConfig(
        code=GERMAN_LANGUAGE.code,
        display_name=GERMAN_LANGUAGE.display_name,
        field_map=PartialFieldMap(
            text_path="display_text",
            phonetic_path="pronunciation",
            example_sentence_path="extra.example_sentence_de",
        ),
        label=GERMAN_LANGUAGE.label,
        phonetic_label=GERMAN_LANGUAGE.phonetic_label,
        font_path=GERMAN_LANGUAGE.font_path,
        noun_fields=frozenset({"german", "pronunciation", "article"}),
        verb_fields=frozenset({"german", "pronunciation", "partizip_ii", "hilfsverb"}),
        adj_fields=frozenset({"german", "pronunciation"}),
        primary_voice="german_female",
        alternate_voice="german_male",
        extra_display_keys=GERMAN_LANGUAGE.extra_display_keys,
        card_extra_font_keys=dict(GERMAN_LANGUAGE.card_extra_font_keys),
        vocab_source_key="german",
        vocab_phonetic_key="pronunciation",
    ),

    voices=tts_engine.VOICES,

    grammar_progression=tuple(HUN_TO_GER_GRAMMAR_PROGRESSION),

    vocab_dir="vocab/hungarian_german",
    curriculum_file="curriculum/curriculum_hungarian_german.json",

    field_map=FieldMap(source="source", target="target"),


)
