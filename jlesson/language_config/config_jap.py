"""Japanese language configuration."""

from __future__ import annotations

from ._base import PartialFieldMap, PartialLanguageConfig


JAPANESE_LANGUAGE = PartialLanguageConfig(
    code="ja",
    display_name="Japanese",
    field_map=PartialFieldMap(
        text_path="display_text",
        phonetic_path="pronunciation",
        example_sentence_path="extra.example_sentence",
        special_paths={"kanji": "extra.kanji", "masu_form": "extra.masu_form"},
        special_labels={"masu_form": "Polite form"},
    ),
    label="Japanese",
    phonetic_label="Romaji",
    font_path="C:/Windows/Fonts/YuGothB.ttc",
    noun_fields=frozenset({"japanese", "kanji", "romaji"}),
    verb_fields=frozenset({"japanese", "kanji", "romaji", "type", "masu_form"}),
    verb_types=frozenset({"る-verb", "う-verb", "irregular", "な-adj"}),
    adj_fields=frozenset({"japanese", "kanji", "romaji", "type"}),
    adj_types=frozenset({"い-adj", "な-adj"}),
    primary_voice="japanese_female",
    alternate_voice="japanese_male",
    extra_display_keys=("kana", "masu_form"),
    card_extra_font_keys={"kana": "jp_small", "masu_form": "jp_small"},
    vocab_source_key="japanese",
    vocab_phonetic_key="romaji",
    llm_content_hints=(
        "display_text: kanji/mixed-script form (e.g. '家', '引っ越す', '大きい')",
        "tts_text: hiragana/katakana spaced for TTS (e.g. 'いえ', 'ひっこす', 'おおきい')",
        "pronunciation: romaji romanisation using Hepburn style (e.g. 'ie', 'hikkōsu', 'ōkii')",
        "extra.kana: hiragana/katakana reading (e.g. 'いえ', 'ひっこす')",
        "extra.masu_form: polite -masu form for VERBS only (e.g. '引っ越します'); omit for nouns/adjectives",
        "extra.type: for verbs — one of: る-verb, う-verb, irregular; for adjectives — one of: い-adj, な-adj; omit for nouns",
    ),
    rcm_dim_map={
        "verbs": {"dim_1": "type", "dim_2": "masu_form"},
        "adjectives": {"dim_1": "type"},
    },
)
