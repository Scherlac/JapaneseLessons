"""
Unit tests for vocab_generator.py

Covers:
  - validate_vocab_schema — valid vocab, missing fields, invalid verb type
  - generate_vocab        — mocked LLM, saves file, skips save, raises on bad response
  - generate_vocab        — LLM missing 'theme' field gets injected automatically
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from jlesson.vocab_generator import extend_vocab, generate_vocab, validate_vocab_schema
from jlesson.language_config import ENG_JAP_CONFIG
from jlesson.llm_client import ask_llm_json_free

# ── Minimal valid vocab fixture ───────────────────────────────────────────────

_VALID_VOCAB = {
    "theme": "test",
    "nouns": [
        {"english": "water", "japanese": "みず", "kanji": "水", "romaji": "mizu"},
        {"english": "rice",  "japanese": "ごはん", "kanji": "ご飯", "romaji": "gohan"},
    ],
    "verbs": [
        {
            "english": "to eat", "japanese": "たべる", "kanji": "食べる",
            "romaji": "taberu", "type": "る-verb", "masu_form": "食べます",
        },
    ],
    "adjectives": [
        {
            "english": "small", "japanese": "ちいさい", "kanji": "小さい",
            "romaji": "chiisai", "type": "い-adj",
        }
    ],
}


def _vocab(**overrides) -> dict:
    """Return a copy of _VALID_VOCAB with optional overrides applied at top level."""
    import copy
    v = copy.deepcopy(_VALID_VOCAB)
    v.update(overrides)
    return v


# ── validate_vocab_schema ─────────────────────────────────────────────────────

class TestValidateVocabSchema:
    def test_valid_vocab_returns_no_errors(self):
        assert validate_vocab_schema(_VALID_VOCAB, ENG_JAP_CONFIG) == []

    def test_missing_theme_field(self):
        vocab = _vocab()
        del vocab["theme"]
        errors = validate_vocab_schema(vocab, ENG_JAP_CONFIG)
        assert any("theme" in e for e in errors)

    def test_missing_nouns_key(self):
        vocab = _vocab()
        del vocab["nouns"]
        errors = validate_vocab_schema(vocab, ENG_JAP_CONFIG)
        assert any("nouns" in e for e in errors)

    def test_empty_nouns_list(self):
        vocab = _vocab(nouns=[])
        errors = validate_vocab_schema(vocab, ENG_JAP_CONFIG)
        assert any("nouns" in e for e in errors)

    def test_missing_verbs_key(self):
        vocab = _vocab()
        del vocab["verbs"]
        errors = validate_vocab_schema(vocab, ENG_JAP_CONFIG)
        assert any("verbs" in e for e in errors)

    def test_noun_missing_romaji_field(self):
        import copy
        vocab = copy.deepcopy(_VALID_VOCAB)
        del vocab["nouns"][0]["romaji"]
        errors = validate_vocab_schema(vocab, ENG_JAP_CONFIG)
        assert any("romaji" in e for e in errors)

    def test_verb_missing_masu_form_field(self):
        import copy
        vocab = copy.deepcopy(_VALID_VOCAB)
        del vocab["verbs"][0]["masu_form"]
        errors = validate_vocab_schema(vocab, ENG_JAP_CONFIG)
        assert any("masu_form" in e for e in errors)

    def test_verb_invalid_type(self):
        import copy
        vocab = copy.deepcopy(_VALID_VOCAB)
        vocab["verbs"][0]["type"] = "bad-type"
        errors = validate_vocab_schema(vocab, ENG_JAP_CONFIG)
        assert any("bad-type" in e for e in errors)

    def test_all_valid_verb_types_accepted(self):
        import copy
        for vtype in ("る-verb", "う-verb", "irregular", "な-adj"):
            vocab = copy.deepcopy(_VALID_VOCAB)
            vocab["verbs"][0]["type"] = vtype
            errors = validate_vocab_schema(vocab, ENG_JAP_CONFIG)
            type_errors = [e for e in errors if "type" in e and vtype not in e]
            assert not type_errors, f"Valid type {vtype!r} was rejected: {errors}"

    def test_adjective_invalid_type(self):
        import copy
        vocab = copy.deepcopy(_VALID_VOCAB)
        vocab["adjectives"][0]["type"] = "bad-type"
        errors = validate_vocab_schema(vocab, ENG_JAP_CONFIG)
        assert any("adjectives" in e and "bad-type" in e for e in errors)

    def test_multiple_errors_reported_together(self):
        errors = validate_vocab_schema({"nouns": [], "verbs": []}, ENG_JAP_CONFIG)
        assert len(errors) >= 2


# ── generate_vocab ────────────────────────────────────────────────────────────

class TestGenerateVocab:
    """Mocks ask_llm_json_free so no LLM server is required."""

    def test_returns_valid_vocab_dict(self, tmp_path):
        with patch("jlesson.vocab_generator._base.ask_llm_json_free", return_value=_vocab()) as _:
            result = generate_vocab("test", save=False)
        assert result["theme"] == "test"
        assert len(result["nouns"]) == 2
        assert len(result["verbs"]) == 1

    def test_saves_file_when_save_true(self, tmp_path):
        with patch("jlesson.vocab_generator._base.ask_llm_json_free", return_value=_vocab()):
            generate_vocab("testtheme", save=True, output_dir=tmp_path)
        assert (tmp_path / "testtheme.json").exists()

    def test_saved_file_content_matches_returned_dict(self, tmp_path):
        import json
        with patch("jlesson.vocab_generator._base.ask_llm_json_free", return_value=_vocab()):
            result = generate_vocab("testtheme", save=True, output_dir=tmp_path)
        saved = json.loads((tmp_path / "testtheme.json").read_text(encoding="utf-8"))
        assert saved["theme"] == result["theme"]
        assert len(saved["nouns"]) == len(result["nouns"])

    def test_no_file_written_when_save_false(self, tmp_path):
        with patch("jlesson.vocab_generator._base.ask_llm_json_free", return_value=_vocab()):
            generate_vocab("testtheme", save=False, output_dir=tmp_path)
        assert not (tmp_path / "testtheme.json").exists()

    def test_raises_if_theme_exists_without_allow_overwrite(self, tmp_path):
        existing_path = tmp_path / "testtheme.json"
        existing_path.write_text('{"theme":"testtheme","nouns":[],"verbs":[]}', encoding="utf-8")
        with patch("jlesson.vocab_generator._base.ask_llm_json_free", return_value=_vocab()):
            with pytest.raises(ValueError, match="already exists"):
                generate_vocab("testtheme", save=True, output_dir=tmp_path)

    def test_overwrites_when_allow_overwrite_true(self, tmp_path):
        existing_path = tmp_path / "testtheme.json"
        existing_path.write_text('{"theme":"testtheme","nouns":[],"verbs":[]}', encoding="utf-8")
        with patch("jlesson.vocab_generator._base.ask_llm_json_free", return_value=_vocab()):
            result = generate_vocab(
                "testtheme",
                save=True,
                allow_overwrite=True,
                output_dir=tmp_path,
            )
        saved = json.loads(existing_path.read_text(encoding="utf-8"))
        assert saved["theme"] == result["theme"]
        assert len(saved["nouns"]) == 2
        assert len(saved["verbs"]) == 1

    def test_theme_injected_if_missing_from_llm_response(self, tmp_path):
        """LLM sometimes omits the 'theme' key — generate_vocab should inject it."""
        vocab_without_theme = _vocab()
        del vocab_without_theme["theme"]
        with patch("jlesson.vocab_generator._base.ask_llm_json_free", return_value=vocab_without_theme):
            result = generate_vocab("animals", save=False)
        assert result["theme"] == "animals"

    def test_raises_value_error_on_schema_validation_failure(self):
        bad_response = {"theme": "bad", "nouns": "not-a-list", "verbs": []}
        with patch("jlesson.vocab_generator._base.ask_llm_json_free", return_value=bad_response):
            with pytest.raises(ValueError, match="schema validation"):
                generate_vocab("bad", save=False)

    def test_llm_uses_correct_theme_in_prompt(self):
        """Ask_llm_json_free should be called with a prompt mentioning the theme."""
        with patch("jlesson.vocab_generator._base.ask_llm_json_free", return_value=_vocab()) as mock_llm:
            generate_vocab("animals", save=False)
        call_args = mock_llm.call_args[0][0]
        assert "animals" in call_args

    def test_llm_uses_correct_num_nouns_and_verbs_in_prompt(self):
        with patch("jlesson.vocab_generator._base.ask_llm_json_free", return_value=_vocab()) as mock_llm:
            generate_vocab("animals", num_nouns=8, num_verbs=5, save=False)
        call_args = mock_llm.call_args[0][0]
        assert "8" in call_args
        assert "5" in call_args

    def test_count_distributes_remaining_with_minimum_ratio(self):
        with patch("jlesson.vocab_generator._base.ask_llm_json_free", return_value=_vocab()) as mock_llm:
            generate_vocab(
                "animals",
                num_nouns=10,
                num_verbs=5,
                total_count=30,
                save=False,
            )
        call_args = mock_llm.call_args[0][0]
        assert "19 nouns" in call_args
        assert "10 verbs" in call_args
        assert "1 adjectives" in call_args

    def test_count_distributes_with_adjectives_minimum(self):
        with patch("jlesson.vocab_generator._base.ask_llm_json_free", return_value=_vocab()) as mock_llm:
            generate_vocab(
                "animals",
                num_nouns=50,
                num_verbs=12,
                num_adjectives=8,
                total_count=100,
                save=False,
            )
        call_args = mock_llm.call_args[0][0]
        assert "71 nouns" in call_args
        assert "17 verbs" in call_args
        assert "12 adjectives" in call_args

    def test_prompt_includes_avoid_words(self):
        with patch("jlesson.vocab_generator._base.ask_llm_json_free", return_value=_vocab()) as mock_llm:
            generate_vocab(
                "animals",
                num_nouns=3,
                num_verbs=2,
                num_adjectives=1,
                save=False,
                avoid_english_words=["water", "bread"],
                avoid_target_words=["みず", "パン"],
            )
        call_args = mock_llm.call_args[0][0]
        assert "Avoid reusing these existing source-language words" in call_args
        assert "water" in call_args
        assert "Avoid reusing these existing target-language words/translations" in call_args
        assert "みず" in call_args

    def test_count_only_splits_evenly_when_no_minimums(self):
        with patch("jlesson.vocab_generator._base.ask_llm_json_free", return_value=_vocab()) as mock_llm:
            generate_vocab(
                "animals",
                num_nouns=None,
                num_verbs=None,
                total_count=9,
                save=False,
            )
        call_args = mock_llm.call_args[0][0]
        assert "3 nouns" in call_args
        assert "3 verbs" in call_args
        assert "3 adjectives" in call_args

    def test_count_must_be_greater_than_or_equal_to_minimum_sum(self):
        with pytest.raises(ValueError, match="--count \(10\) must be >= --nouns \+ --verbs \+ --adjectives \(11\)"):
            generate_vocab(
                "animals",
                num_nouns=8,
                num_verbs=3,
                num_adjectives=0,
                total_count=10,
                save=False,
            )

    def test_creates_output_directory_if_missing(self, tmp_path):
        nested = tmp_path / "deep" / "nested"
        with patch("jlesson.vocab_generator._base.ask_llm_json_free", return_value=_vocab()):
            generate_vocab("testtheme", save=True, output_dir=nested)
        assert (nested / "testtheme.json").exists()

    def test_large_request_is_batched_and_merged(self):
        batch_a = {
            "theme": "big",
            "nouns": [
                {"english": "cat", "japanese": "ねこ", "kanji": "猫", "romaji": "neko"},
                {"english": "dog", "japanese": "いぬ", "kanji": "犬", "romaji": "inu"},
            ],
            "verbs": [
                {
                    "english": "to eat", "japanese": "たべる", "kanji": "食べる",
                    "romaji": "taberu", "type": "る-verb", "masu_form": "食べます",
                }
            ],
        }
        batch_b = {
            "theme": "big",
            "nouns": [
                {"english": "dog", "japanese": "いぬ", "kanji": "犬", "romaji": "inu"},
                {"english": "bird", "japanese": "とり", "kanji": "鳥", "romaji": "tori"},
            ],
            "verbs": [
                {
                    "english": "to drink", "japanese": "のむ", "kanji": "飲む",
                    "romaji": "nomu", "type": "う-verb", "masu_form": "飲みます",
                }
            ],
        }
        with patch("jlesson.vocab_generator._base._MAX_NOUNS_PER_REQUEST", 2), \
             patch("jlesson.vocab_generator._base._MAX_VERBS_PER_REQUEST", 1), \
             patch("jlesson.vocab_generator._base.ask_llm_json_free", side_effect=[batch_a, batch_b]):
            result = generate_vocab("big", num_nouns=3, num_verbs=2, save=False)
        assert [n["english"] for n in result["nouns"]] == ["cat", "dog", "bird"]
        assert [v["english"] for v in result["verbs"]] == ["to eat", "to drink"]

    def test_shortfall_saves_partial_file(self, tmp_path):
        # First batch yields one noun/verb; top-up returns duplicates only.
        first = {
            "theme": "big",
            "nouns": [{"english": "cat", "japanese": "ねこ", "kanji": "猫", "romaji": "neko"}],
            "verbs": [{
                "english": "to eat", "japanese": "たべる", "kanji": "食べる",
                "romaji": "taberu", "type": "る-verb", "masu_form": "食べます",
            }],
        }
        duplicate = {
            "theme": "big",
            "nouns": [{"english": "cat", "japanese": "ねこ", "kanji": "猫", "romaji": "neko"}],
            "verbs": [{
                "english": "to eat", "japanese": "たべる", "kanji": "食べる",
                "romaji": "taberu", "type": "る-verb", "masu_form": "食べます",
            }],
        }

        with patch("jlesson.vocab_generator._base._MAX_NOUNS_PER_REQUEST", 2), \
             patch("jlesson.vocab_generator._base._MAX_VERBS_PER_REQUEST", 1), \
             patch(
                 "jlesson.vocab_generator._base.ask_llm_json_free",
                 side_effect=[first, duplicate, duplicate, duplicate, duplicate],
             ):
            with pytest.raises(ValueError, match="Partial output saved to"):
                generate_vocab("big", num_nouns=3, num_verbs=2, save=True, output_dir=tmp_path)

        assert (tmp_path / "big.partial.json").exists()


class TestAskLlmJsonFree:
    def test_empty_response_error_is_explicit(self):
        class _DummyClient:
            def generate_text(self, **kwargs):
                return ""

        with patch("jlesson.llm_client.get_llm_client", return_value=_DummyClient()):
            with pytest.raises(ValueError, match="<empty response from model>"):
                ask_llm_json_free("Return JSON")


class TestExtendVocab:
    def test_extend_merges_unique_items_and_saves(self, tmp_path):
        existing = {
            "theme": "testtheme",
            "nouns": [{"english": "water", "japanese": "みず", "kanji": "水", "romaji": "mizu"}],
            "verbs": [{
                "english": "to eat", "japanese": "たべる", "kanji": "食べる",
                "romaji": "taberu", "type": "る-verb", "masu_form": "食べます",
            }],
            "adjectives": [{
                "english": "small", "japanese": "ちいさい", "kanji": "小さい",
                "romaji": "chiisai", "type": "い-adj",
            }],
            "others": [{
                "english": "hello", "japanese": "こんにちは", "kanji": "今日は",
                "romaji": "konnichiwa", "category": "expression",
            }],
        }
        (tmp_path / "testtheme.json").write_text(json.dumps(existing, ensure_ascii=False), encoding="utf-8")

        generated = {
            "theme": "testtheme",
            "nouns": [
                {"english": "water", "japanese": "みず", "kanji": "水", "romaji": "mizu"},
                {"english": "bread", "japanese": "パン", "kanji": "パン", "romaji": "pan"},
            ],
            "verbs": [
                {
                    "english": "to eat", "japanese": "たべる", "kanji": "食べる",
                    "romaji": "taberu", "type": "る-verb", "masu_form": "食べます",
                },
                {
                    "english": "to drink", "japanese": "のむ", "kanji": "飲む",
                    "romaji": "nomu", "type": "う-verb", "masu_form": "飲みます",
                },
            ],
            "adjectives": [
                {
                    "english": "small", "japanese": "ちいさい", "kanji": "小さい",
                    "romaji": "chiisai", "type": "い-adj",
                },
                {
                    "english": "fast", "japanese": "はやい", "kanji": "速い",
                    "romaji": "hayai", "type": "い-adj",
                },
            ],
            "others": [
                {
                    "english": "hello", "japanese": "こんにちは", "kanji": "今日は",
                    "romaji": "konnichiwa", "category": "expression",
                },
                {
                    "english": "thanks", "japanese": "ありがとう", "kanji": "有難う",
                    "romaji": "arigatou", "category": "expression",
                },
            ],
        }

        with patch("jlesson.vocab_generator._base.generate_vocab", return_value=generated):
            merged = extend_vocab("testtheme", add_nouns=2, add_verbs=2, output_dir=tmp_path)

        assert len(merged["nouns"]) == 2
        assert len(merged["verbs"]) == 2
        assert len(merged["adjectives"]) == 2
        assert len(merged["others"]) == 2
        saved = json.loads((tmp_path / "testtheme.json").read_text(encoding="utf-8"))
        assert len(saved["nouns"]) == 2
        assert len(saved["verbs"]) == 2
        assert len(saved["adjectives"]) == 2
        assert len(saved["others"]) == 2

    def test_extend_missing_theme_raises_value_error(self, tmp_path):
        with pytest.raises(ValueError, match="Cannot extend missing theme"):
            extend_vocab("does-not-exist", output_dir=tmp_path)

    def test_extend_passes_existing_words_to_generate(self, tmp_path):
        existing = {
            "theme": "testtheme",
            "nouns": [{"english": "water", "japanese": "みず", "kanji": "水", "romaji": "mizu"}],
            "verbs": [{
                "english": "to eat", "japanese": "たべる", "kanji": "食べる",
                "romaji": "taberu", "type": "る-verb", "masu_form": "食べます",
            }],
        }
        (tmp_path / "testtheme.json").write_text(json.dumps(existing, ensure_ascii=False), encoding="utf-8")

        def _fake_generate_vocab(**kwargs):
            assert "water" in kwargs.get("avoid_english_words", [])
            assert "みず" in kwargs.get("avoid_target_words", [])
            return {
                "theme": "testtheme",
                "nouns": [{"english": "bread", "japanese": "パン", "kanji": "パン", "romaji": "pan"}],
                "verbs": [{
                    "english": "to eat", "japanese": "たべる", "kanji": "食べる",
                    "romaji": "taberu", "type": "る-verb", "masu_form": "食べます",
                }],
                "adjectives": [],
                "others": [],
            }

        with patch("jlesson.vocab_generator._base.generate_vocab", side_effect=_fake_generate_vocab):
            merged = extend_vocab("testtheme", add_nouns=1, add_verbs=0, output_dir=tmp_path)
        assert any(n["english"] == "bread" for n in merged["nouns"])
