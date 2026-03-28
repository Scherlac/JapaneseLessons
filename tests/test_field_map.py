"""Unit tests for split role field mapping on language configs."""

from __future__ import annotations

from jlesson.language_config import FieldMap, PartialFieldMap, PartialLanguageConfig, get_language_config
from jlesson.models import GeneralItem, PartialItem


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ENG_JAP = get_language_config("eng-jap")
HUN_ENG = get_language_config("hun-eng")


def _jap_noun() -> GeneralItem:
    return GeneralItem(
        source=PartialItem(display_text="cat", extra={"example_sentence_en": "I like cats."}),
        target=PartialItem(display_text="猫", pronunciation="neko", extra={"kanji": "猫", "example_sentence_jp": "猫が好きです。"}),
    )


def _hun_noun() -> GeneralItem:
    """GeneralItem with Hungarian extra fields."""
    return GeneralItem(
        source=PartialItem(display_text="macska", extra={"example_sentence_hu": "Szeretem a macskákat."}),
        target=PartialItem(display_text="cat", pronunciation="/ˈmɒtʃkɒ/", extra={"example_sentence_en": "I like cats."}),
    )


# ---------------------------------------------------------------------------
# LanguageConfig.view — Pydantic model inputs
# ---------------------------------------------------------------------------

class TestFieldMapViewPydanticModel:
    def test_eng_jap_noun_source(self):
        v = ENG_JAP.view(_jap_noun())
        assert v["source"] == "cat"

    def test_eng_jap_noun_target(self):
        v = ENG_JAP.view(_jap_noun())
        assert v["target"] == "猫"

    def test_eng_jap_noun_phonetic(self):
        v = ENG_JAP.view(_jap_noun())
        assert v["target_phonetic"] == "neko"

    def test_eng_jap_noun_example_target(self):
        v = ENG_JAP.view(_jap_noun())
        assert v["example_sentence_target"] == "猫が好きです。"

    def test_eng_jap_noun_example_source(self):
        v = ENG_JAP.view(_jap_noun())
        assert v["example_sentence_source"] == "I like cats."

    def test_eng_jap_target_special_kanji(self):
        v = ENG_JAP.view(_jap_noun())
        assert v["target_special"]["kanji"] == "猫"

    def test_hun_eng_noun_source_is_hungarian(self):
        v = HUN_ENG.view(_hun_noun())
        assert v["source"] == "macska"

    def test_hun_eng_noun_target_is_english(self):
        v = HUN_ENG.view(_hun_noun())
        assert v["target"] == "cat"

    def test_hun_eng_noun_phonetic(self):
        v = HUN_ENG.view(_hun_noun())
        assert v["target_phonetic"] == "/ˈmɒtʃkɒ/"

    def test_hun_eng_noun_example_target(self):
        v = HUN_ENG.view(_hun_noun())
        assert v["example_sentence_target"] == "I like cats."

    def test_hun_eng_noun_example_source(self):
        v = HUN_ENG.view(_hun_noun())
        assert v["example_sentence_source"] == "Szeretem a macskákat."


# ---------------------------------------------------------------------------
# LanguageConfig.view — plain dict inputs (used by report builder)
# ---------------------------------------------------------------------------

class TestFieldMapViewDict:
    def test_eng_jap_dict(self):
        d = {
            "source": {"display_text": "dog", "extra": {"example_sentence_en": "There is a dog."}},
            "target": {"display_text": "犬", "pronunciation": "inu", "extra": {"kanji": "犬", "example_sentence_jp": "犬がいます。"}},
        }
        v = ENG_JAP.view(d)
        assert v["source"] == "dog"
        assert v["target"] == "犬"
        assert v["target_phonetic"] == "inu"
        assert v["target_special"]["kanji"] == "犬"
        assert v["example_sentence_target"] == "犬がいます。"

    def test_hun_eng_dict(self):
        d = {
            "source": {"display_text": "kutya", "extra": {"example_sentence_hu": "Van egy kutya."}},
            "target": {"display_text": "dog", "pronunciation": "/ˈkutjɒ/", "extra": {"example_sentence_en": "There is a dog."}},
        }
        v = HUN_ENG.view(d)
        assert v["source"] == "kutya"
        assert v["target"] == "dog"
        assert v["target_phonetic"] == "/ˈkutjɒ/"
        assert v["example_sentence_source"] == "Van egy kutya."

    def test_missing_field_returns_empty_string(self):
        d = {"source": {"display_text": "fish"}}
        v = ENG_JAP.view(d)
        assert v["target"] == ""
        assert v["target_phonetic"] == ""


# ---------------------------------------------------------------------------
# FieldMap labels
# ---------------------------------------------------------------------------

class TestFieldMapLabels:
    def test_eng_jap_labels(self):
        assert ENG_JAP.source_label == "English"
        assert ENG_JAP.target_label == "Japanese"
        assert ENG_JAP.phonetic_label == "Romaji"

    def test_hun_eng_labels(self):
        assert HUN_ENG.source_label == "Magyar"
        assert HUN_ENG.target_label == "English"
        assert HUN_ENG.phonetic_label == "Pronunciation"


# ---------------------------------------------------------------------------
# FieldMap target_special
# ---------------------------------------------------------------------------

class TestFieldMapTargetSpecial:
    def test_eng_jap_has_kanji_and_masu(self):
        assert "kanji" in ENG_JAP.target_special_paths
        assert "masu_form" in ENG_JAP.target_special_paths

    def test_hun_eng_no_target_special(self):
        assert HUN_ENG.target_special_paths == {}

    def test_masu_form_via_view(self):
        verb = GeneralItem(
            source=PartialItem(display_text="to eat"),
            target=PartialItem(display_text="たべる", pronunciation="taberu", extra={"kanji": "食べる", "masu_form": "食べます"}),
        )
        v = ENG_JAP.view(verb)
        assert v["target_special"]["masu_form"] == "食べます"


# ---------------------------------------------------------------------------
# FieldMap — empty field_name guard
# ---------------------------------------------------------------------------

class TestFieldMapEmptyFieldName:
    def test_empty_phonetic_returns_empty(self):
        fm = FieldMap(source="english", target="japanese")
        v = fm.view({"english": "tree", "japanese": "木"})
        assert v["target_phonetic"] == ""

    def test_empty_example_returns_empty(self):
        fm = FieldMap(source="english", target="japanese")
        v = fm.view({"english": "tree", "japanese": "木"})
        assert v["example_sentence_source"] == ""
        assert v["example_sentence_target"] == ""

    def test_relative_paths_can_be_supplied_from_partial_config(self):
        fm = FieldMap(source="source", target="target")
        source_cfg = PartialLanguageConfig(
            code="en",
            display_name="English",
            field_map=PartialFieldMap(text_path="display_text", example_sentence_path="extra.example_sentence_en"),
        )
        target_cfg = PartialLanguageConfig(
            code="ja",
            display_name="Japanese",
            field_map=PartialFieldMap(text_path="display_text", phonetic_path="pronunciation"),
        )
        item = {
            "source": {"display_text": "tree", "extra": {"example_sentence_en": "A tree."}},
            "target": {"display_text": "木", "pronunciation": "ki"},
        }
        v = fm.view(item, source_cfg.field_map, target_cfg.field_map)
        assert v["source"] == "tree"
        assert v["example_sentence_source"] == "A tree."
        assert v["target_phonetic"] == "ki"


# ---------------------------------------------------------------------------
# Voice keys now live on partial language configs
# ---------------------------------------------------------------------------

class TestFieldMapVoices:
    def test_eng_jap_source_voice(self):
        assert ENG_JAP.source.primary_voice == "english_female"

    def test_eng_jap_target_voice_female(self):
        assert ENG_JAP.target.primary_voice == "japanese_female"

    def test_eng_jap_target_voice_male(self):
        assert ENG_JAP.target.alternate_voice == "japanese_male"

    def test_hun_eng_source_voice(self):
        assert HUN_ENG.source.primary_voice == "hungarian_female"

    def test_hun_eng_target_voice_female(self):
        assert HUN_ENG.target.primary_voice == "english_uk_female"

    def test_hun_eng_target_voice_male(self):
        assert HUN_ENG.target.alternate_voice == "english_uk_male"

    def test_source_voice_key_in_config_voices(self):
        for cfg in (ENG_JAP, HUN_ENG):
            assert cfg.source.primary_voice in cfg.voices

    def test_target_voice_female_key_in_config_voices(self):
        for cfg in (ENG_JAP, HUN_ENG):
            assert cfg.target.primary_voice in cfg.voices

    def test_target_voice_male_key_in_config_voices(self):
        for cfg in (ENG_JAP, HUN_ENG):
            assert cfg.target.alternate_voice in cfg.voices
