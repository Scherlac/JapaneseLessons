"""Tests for split source/target language configuration composition."""

from jlesson.language_config import ENG_JAP_CONFIG, HUN_ENG_CONFIG, PartialLanguageConfig


def test_pair_configs_expose_partial_language_configs():
    assert isinstance(ENG_JAP_CONFIG.source, PartialLanguageConfig)
    assert isinstance(ENG_JAP_CONFIG.target, PartialLanguageConfig)
    assert isinstance(HUN_ENG_CONFIG.source, PartialLanguageConfig)
    assert isinstance(HUN_ENG_CONFIG.target, PartialLanguageConfig)


def test_eng_jap_partial_configs_preserve_existing_schema():
    assert ENG_JAP_CONFIG.source.display_name == "English"
    assert ENG_JAP_CONFIG.target.display_name == "Japanese"
    assert ENG_JAP_CONFIG.vocab_noun_fields == frozenset({"english", "japanese", "kanji", "romaji"})
    assert ENG_JAP_CONFIG.target.font_path == ENG_JAP_CONFIG.target_font_path
    assert ENG_JAP_CONFIG.source.font_path == ENG_JAP_CONFIG.native_font_path
    assert ENG_JAP_CONFIG.source_label == "English"
    assert ENG_JAP_CONFIG.target_label == "Japanese"
    assert ENG_JAP_CONFIG.phonetic_label == "Romaji"


def test_hun_eng_partial_configs_preserve_existing_schema():
    assert HUN_ENG_CONFIG.source.display_name == "Hungarian"
    assert HUN_ENG_CONFIG.target.display_name == "English"
    assert HUN_ENG_CONFIG.vocab_verb_fields == frozenset({"english", "hungarian", "pronunciation", "past_tense"})
    assert HUN_ENG_CONFIG.target.primary_voice == HUN_ENG_CONFIG.target_voice_female
    assert HUN_ENG_CONFIG.source.primary_voice == HUN_ENG_CONFIG.source_voice
    assert HUN_ENG_CONFIG.target_extra_display_keys == []