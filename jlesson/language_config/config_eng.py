"""English language configuration."""

from __future__ import annotations

from ._base import PartialFieldMap, PartialLanguageConfig


ENGLISH_LANGUAGE = PartialLanguageConfig(
    code="en",
    display_name="English",
    field_map=PartialFieldMap(
        text_path="display_text",
        phonetic_path="pronunciation"
    ),
    label="English",
    phonetic_label="IPA",
    font_path="C:/Windows/Fonts/segoeui.ttf",
    noun_fields=frozenset({"english", "pronunciation"}),
    verb_fields=frozenset({"english", "pronunciation", "past_tense"}),
    adj_fields=frozenset({"english", "pronunciation"}),
    primary_voice="english_female",
    alternate_voice="english_male",
    vocab_source_key="english",
    vocab_phonetic_key="pronunciation",
    llm_content_hints=(
        "display_text: natural dictionary form (e.g. 'house', 'to move', 'big')",
        "tts_text: full spoken form for TTS (e.g. 'the house', 'to move', 'big')",
        "pronunciation: IPA transcription (e.g. 'haʊs', 'muːv', 'bɪɡ')",
        "extra.past_tense: past tense form (verbs only, e.g. 'moved', 'ate')",
    ),
)
