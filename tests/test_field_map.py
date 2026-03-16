"""Unit tests for FieldMap — the language-agnostic field-role mapping layer."""

from __future__ import annotations

import pytest

from jlesson.language_config import FieldMap, get_language_config
from jlesson.models import NounItem, VerbItem, Sentence


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ENG_JAP = get_language_config("eng-jap")
HUN_ENG = get_language_config("hun-eng")


def _jap_noun() -> NounItem:
    return NounItem(
        english="cat",
        japanese="猫",
        kanji="猫",
        romaji="neko",
        example_sentence_jp="猫が好きです。",
        example_sentence_en="I like cats.",
        memory_tip="Think of 'neck-oh'",
    )


def _hun_noun() -> NounItem:
    """NounItem with Hungarian extra fields stored via extra='allow'."""
    return NounItem.model_validate({
        "english": "cat",
        "hungarian": "macska",
        "pronunciation": "/ˈmɒtʃkɒ/",
        "example_sentence_en": "I like cats.",
        "example_sentence_hu": "Szeretem a macskákat.",
        "memory_tip": "Sounds like 'match-ka'",
    })


# ---------------------------------------------------------------------------
# FieldMap.view — Pydantic model inputs
# ---------------------------------------------------------------------------

class TestFieldMapViewPydanticModel:
    def test_eng_jap_noun_source(self):
        v = ENG_JAP.field_map.view(_jap_noun())
        assert v["source"] == "cat"

    def test_eng_jap_noun_target(self):
        v = ENG_JAP.field_map.view(_jap_noun())
        assert v["target"] == "猫"

    def test_eng_jap_noun_phonetic(self):
        v = ENG_JAP.field_map.view(_jap_noun())
        assert v["target_phonetic"] == "neko"

    def test_eng_jap_noun_example_target(self):
        v = ENG_JAP.field_map.view(_jap_noun())
        assert v["example_sentence_target"] == "猫が好きです。"

    def test_eng_jap_noun_example_source(self):
        v = ENG_JAP.field_map.view(_jap_noun())
        assert v["example_sentence_source"] == "I like cats."

    def test_eng_jap_target_special_kanji(self):
        v = ENG_JAP.field_map.view(_jap_noun())
        assert v["target_special"]["kanji"] == "猫"

    def test_hun_eng_noun_source_is_hungarian(self):
        v = HUN_ENG.field_map.view(_hun_noun())
        assert v["source"] == "macska"

    def test_hun_eng_noun_target_is_english(self):
        v = HUN_ENG.field_map.view(_hun_noun())
        assert v["target"] == "cat"

    def test_hun_eng_noun_phonetic(self):
        v = HUN_ENG.field_map.view(_hun_noun())
        assert v["target_phonetic"] == "/ˈmɒtʃkɒ/"

    def test_hun_eng_noun_example_target(self):
        v = HUN_ENG.field_map.view(_hun_noun())
        assert v["example_sentence_target"] == "I like cats."

    def test_hun_eng_noun_example_source(self):
        v = HUN_ENG.field_map.view(_hun_noun())
        assert v["example_sentence_source"] == "Szeretem a macskákat."


# ---------------------------------------------------------------------------
# FieldMap.view — plain dict inputs (used by report builder)
# ---------------------------------------------------------------------------

class TestFieldMapViewDict:
    def test_eng_jap_dict(self):
        d = {
            "english": "dog",
            "japanese": "犬",
            "romaji": "inu",
            "kanji": "犬",
            "example_sentence_jp": "犬がいます。",
            "example_sentence_en": "There is a dog.",
        }
        v = ENG_JAP.field_map.view(d)
        assert v["source"] == "dog"
        assert v["target"] == "犬"
        assert v["target_phonetic"] == "inu"
        assert v["target_special"]["kanji"] == "犬"
        assert v["example_sentence_target"] == "犬がいます。"

    def test_hun_eng_dict(self):
        d = {
            "hungarian": "kutya",
            "english": "dog",
            "pronunciation": "/ˈkutjɒ/",
            "example_sentence_en": "There is a dog.",
            "example_sentence_hu": "Van egy kutya.",
        }
        v = HUN_ENG.field_map.view(d)
        assert v["source"] == "kutya"
        assert v["target"] == "dog"
        assert v["target_phonetic"] == "/ˈkutjɒ/"
        assert v["example_sentence_source"] == "Van egy kutya."

    def test_missing_field_returns_empty_string(self):
        d = {"english": "fish"}
        v = ENG_JAP.field_map.view(d)
        assert v["target"] == ""
        assert v["target_phonetic"] == ""


# ---------------------------------------------------------------------------
# FieldMap labels
# ---------------------------------------------------------------------------

class TestFieldMapLabels:
    def test_eng_jap_labels(self):
        fm = ENG_JAP.field_map
        assert fm.source_label == "English"
        assert fm.target_label == "Japanese"
        assert fm.phonetic_label == "Romaji"

    def test_hun_eng_labels(self):
        fm = HUN_ENG.field_map
        assert fm.source_label == "Magyar"
        assert fm.target_label == "English"
        assert fm.phonetic_label == "Pronunciation"


# ---------------------------------------------------------------------------
# FieldMap target_special
# ---------------------------------------------------------------------------

class TestFieldMapTargetSpecial:
    def test_eng_jap_has_kanji_and_masu(self):
        fm = ENG_JAP.field_map
        assert "kanji" in fm.target_special
        assert "masu_form" in fm.target_special

    def test_hun_eng_no_target_special(self):
        fm = HUN_ENG.field_map
        assert fm.target_special == {}

    def test_masu_form_via_view(self):
        verb = VerbItem(
            english="to eat",
            japanese="たべる",
            kanji="食べる",
            romaji="taberu",
            masu_form="食べます",
        )
        v = ENG_JAP.field_map.view(verb)
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
