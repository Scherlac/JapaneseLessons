"""French language configuration."""

from __future__ import annotations

from ._base import PartialFieldMap, PartialLanguageConfig


FRENCH_LANGUAGE = PartialLanguageConfig(
    code="fr",
    display_name="French",
    field_map=PartialFieldMap(
        text_path="display_text",
        phonetic_path="pronunciation"
    ),
    label="Français",
    phonetic_label="IPA",
    font_path="C:/Windows/Fonts/segoeui.ttf",
    noun_fields=frozenset({"french", "pronunciation", "article"}),
    verb_fields=frozenset({"french", "pronunciation", "past_participle", "auxiliary"}),
    adj_fields=frozenset({"french", "pronunciation"}),
    primary_voice="french_female",
    alternate_voice="french_male",
    extra_display_keys=("article",),
    card_extra_font_keys={"article": "en_small"},
    vocab_source_key="french",
    vocab_phonetic_key="pronunciation",
    llm_content_hints=(
        "display_text: plain dictionary form (e.g. 'maison', 'manger', 'grand')",
        "tts_text: natural spoken form for TTS (e.g. 'la maison', 'manger', 'grand')",
        "pronunciation: IPA transcription (e.g. 'mɛzɔ̃', 'mɑ̃ʒe', 'ɡʁɑ̃')",
        "extra.article: definite article — le/la/les (nouns only)",
        "extra.past_participle: past participle form (verbs only, e.g. 'mangé')",
        "extra.auxiliary: auxiliary verb — avoir or être (verbs only)",
    ),
    rcm_dim_map={
        "verbs": {"dim_1": "auxiliary", "dim_2": "past_participle"},
        "nouns": {"dim_1": "article"},
    },
)
