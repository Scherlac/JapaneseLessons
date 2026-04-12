"""Hungarian language configuration."""

from __future__ import annotations

from ._base import PartialFieldMap, PartialLanguageConfig


HUNGARIAN_LANGUAGE = PartialLanguageConfig(
    code="hu",
    display_name="Hungarian",
    field_map=PartialFieldMap(
        text_path="display_text",
        example_sentence_path="extra.example_sentence_hu",
    ),
    label="Magyar",
    font_path="C:/Windows/Fonts/segoeui.ttf",
    noun_fields=frozenset({"hungarian"}),
    verb_fields=frozenset({"hungarian"}),
    adj_fields=frozenset({"hungarian"}),
    primary_voice="hungarian_female",
    vocab_source_key="hungarian",
)
