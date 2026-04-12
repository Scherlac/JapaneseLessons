"""German language configuration."""

from __future__ import annotations

from ._base import PartialFieldMap, PartialLanguageConfig


GERMAN_LANGUAGE = PartialLanguageConfig(
    code="de",
    display_name="German",
    field_map=PartialFieldMap(
        text_path="display_text",
        phonetic_path="pronunciation",
        example_sentence_path="extra.example_sentence_de",
    ),
    label="Deutsch",
    phonetic_label="Aussprache",
    font_path="C:/Windows/Fonts/segoeui.ttf",
    noun_fields=frozenset({"german", "pronunciation", "article"}),
    verb_fields=frozenset({"german", "pronunciation", "partizip_ii", "hilfsverb"}),
    adj_fields=frozenset({"german", "pronunciation"}),
    primary_voice="german_female",
    alternate_voice="german_male",
    extra_display_keys=("article",),
    card_extra_font_keys={"article": "en_small"},
    vocab_source_key="german",
    vocab_phonetic_key="pronunciation",
    llm_content_hints=(
        "display_text: plain dictionary form (e.g. 'Haus', 'gehen', 'groß')",
        "tts_text: natural spoken form for TTS (e.g. 'das Haus', 'gehen', 'groß')",
        "pronunciation: IPA transcription (e.g. 'haʊs', 'ˈɡeːən', 'ɡroːs')",
        "extra.article: grammatical article — der/die/das (nouns only)",
        "extra.partizip_ii: past participle form (verbs only, e.g. 'gegangen')",
        "extra.hilfsverb: auxiliary verb — haben or sein (verbs only)"
    ),
    rcm_dim_map={
        "verbs": {"dim_1": "hilfsverb", "dim_2": "partizip_ii"},
        "nouns": {"dim_1": "article"},
    },
)
