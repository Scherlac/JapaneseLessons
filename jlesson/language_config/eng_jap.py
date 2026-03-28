"""Language configuration for the English → Japanese language pair."""

from __future__ import annotations

from jlesson.video import tts_engine

from ..curriculum import ENG_TO_JAP_GRAMMAR_PROGRESSION
from ..item_generator import EngJapItemGenerator
from ..prompt_template import EngJapPrompts, PERSONS_BEGINNER
from ._base import FieldMap, LanguageConfig

ENG_JAP_CONFIG = LanguageConfig(
    code="eng-jap",
    display_name="English-Japanese",
    target_language="Japanese",
    native_language="English",

    vocab_noun_fields=frozenset({"english", "japanese", "kanji", "romaji"}),
    vocab_verb_fields=frozenset({"english", "japanese", "kanji", "romaji", "type", "masu_form"}),
    vocab_verb_types=frozenset({"る-verb", "う-verb", "irregular", "な-adj"}),
    vocab_adj_fields=frozenset({"english", "japanese", "kanji", "romaji", "type"}),
    vocab_adj_types=frozenset({"い-adj", "な-adj"}),

    voices=tts_engine.VOICES,

    target_font_path="C:/Windows/Fonts/YuGothB.ttc",
    native_font_path="C:/Windows/Fonts/segoeui.ttf",

    grammar_progression=tuple(ENG_TO_JAP_GRAMMAR_PROGRESSION),
    persons=tuple(PERSONS_BEGINNER),

    vocab_dir="vocab",
    curriculum_file="curriculum/curriculum.json",

    field_map=FieldMap(
        source="source.display_text",
        target="target.display_text",
        target_phonetic="target.pronunciation",
        target_special={"kanji": "target.kanji", "masu_form": "target.masu_form"},
        example_sentence_source="source.extra.example_sentence_en",
        example_sentence_target="target.extra.example_sentence_jp",
        source_label="English",
        target_label="Japanese",
        phonetic_label="Romaji",
        source_voice="english_female",
        target_voice_female="japanese_female",
        target_voice_male="japanese_male",
        extra_display_keys=["kana", "masu_form"],
        card_extra_font_keys={"kana": "jp_small", "masu_form": "jp_small"},
    ),

    generator=EngJapItemGenerator(),
    prompts=EngJapPrompts(),
)
