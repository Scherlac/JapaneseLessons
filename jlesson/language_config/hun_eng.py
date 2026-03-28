"""Language configuration for the Hungarian → English language pair."""

from __future__ import annotations

from jlesson.video import tts_engine

from ..curriculum import HUN_TO_ENG_GRAMMAR_PROGRESSION
from ..item_generator import HunEngItemGenerator
from ..prompt_template import HunEngPrompts, HUNGARIAN_PERSONS
from ._base import FieldMap, LanguageConfig

HUN_ENG_CONFIG = LanguageConfig(
    code="hun-eng",
    display_name="Hungarian-English",
    target_language="English",
    native_language="Hungarian",

    vocab_noun_fields=frozenset({"english", "hungarian", "pronunciation"}),
    vocab_verb_fields=frozenset({"english", "hungarian", "pronunciation", "past_tense"}),
    vocab_verb_types=frozenset(),  # English verbs don't use Japanese-style type classes
    vocab_adj_fields=frozenset({"english", "hungarian", "pronunciation"}),
    vocab_adj_types=frozenset(),   # English adjectives don't require type classification

    voices=tts_engine.VOICES,

    target_font_path="C:/Windows/Fonts/segoeui.ttf",
    native_font_path="C:/Windows/Fonts/segoeui.ttf",

    grammar_progression=tuple(HUN_TO_ENG_GRAMMAR_PROGRESSION),
    persons=tuple(HUNGARIAN_PERSONS),

    vocab_dir="vocab/hungarian",
    curriculum_file="curriculum/curriculum_hungarian.json",

    field_map=FieldMap(
        source="source.display_text",
        target="target.display_text",
        target_phonetic="target.pronunciation",
        target_special={},
        example_sentence_source="source.extra.example_sentence_hu",
        example_sentence_target="target.extra.example_sentence_en",
        source_label="Magyar",
        target_label="English",
        phonetic_label="Pronunciation",
        source_voice="hungarian_female",
        target_voice_female="english_uk_female",
        target_voice_male="english_uk_male",
        extra_display_keys=[],
        card_extra_font_keys={},
    ),

    generator=HunEngItemGenerator(),
    prompts=HunEngPrompts(),
)
