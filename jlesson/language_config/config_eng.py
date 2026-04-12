"""English language configuration."""

from __future__ import annotations

from ._base import PartialFieldMap, PartialLanguageConfig


ENGLISH_LANGUAGE = PartialLanguageConfig(
    code="en",
    display_name="English",
    field_map=PartialFieldMap(
        text_path="display_text",
        phonetic_path="pronunciation",
        example_sentence_path="extra.example_sentence_en",
    ),
    label="English",
    phonetic_label="Pronunciation",
    font_path="C:/Windows/Fonts/segoeui.ttf",
    noun_fields=frozenset({"english"}),
    verb_fields=frozenset({"english"}),
    adj_fields=frozenset({"english"}),
    primary_voice="english_female",
    alternate_voice="english_male",
    vocab_source_key="english",
    llm_content_hints=(
        "display_text: natural dictionary form (e.g. 'house', 'to move', 'big')",
        "tts_text: full spoken form for TTS (e.g. 'the house', 'to move', 'big')",
        "pronunciation: stressed syllable guide (e.g. 'HOW-ss', 'to MOOV', 'BIG')",
    ),
)
