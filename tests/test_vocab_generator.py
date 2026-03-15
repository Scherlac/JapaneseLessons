"""
Unit tests for vocab_generator.py

Covers:
  - validate_vocab_schema — valid vocab, missing fields, invalid verb type
  - generate_vocab        — mocked LLM, saves file, skips save, raises on bad response
  - generate_vocab        — LLM missing 'theme' field gets injected automatically
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from jlesson.vocab_generator import generate_vocab, validate_vocab_schema

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
        assert validate_vocab_schema(_VALID_VOCAB) == []

    def test_missing_theme_field(self):
        vocab = _vocab()
        del vocab["theme"]
        errors = validate_vocab_schema(vocab)
        assert any("theme" in e for e in errors)

    def test_missing_nouns_key(self):
        vocab = _vocab()
        del vocab["nouns"]
        errors = validate_vocab_schema(vocab)
        assert any("nouns" in e for e in errors)

    def test_empty_nouns_list(self):
        vocab = _vocab(nouns=[])
        errors = validate_vocab_schema(vocab)
        assert any("nouns" in e for e in errors)

    def test_missing_verbs_key(self):
        vocab = _vocab()
        del vocab["verbs"]
        errors = validate_vocab_schema(vocab)
        assert any("verbs" in e for e in errors)

    def test_noun_missing_romaji_field(self):
        import copy
        vocab = copy.deepcopy(_VALID_VOCAB)
        del vocab["nouns"][0]["romaji"]
        errors = validate_vocab_schema(vocab)
        assert any("romaji" in e for e in errors)

    def test_verb_missing_masu_form_field(self):
        import copy
        vocab = copy.deepcopy(_VALID_VOCAB)
        del vocab["verbs"][0]["masu_form"]
        errors = validate_vocab_schema(vocab)
        assert any("masu_form" in e for e in errors)

    def test_verb_invalid_type(self):
        import copy
        vocab = copy.deepcopy(_VALID_VOCAB)
        vocab["verbs"][0]["type"] = "bad-type"
        errors = validate_vocab_schema(vocab)
        assert any("bad-type" in e for e in errors)

    def test_all_valid_verb_types_accepted(self):
        import copy
        for vtype in ("る-verb", "う-verb", "irregular", "な-adj"):
            vocab = copy.deepcopy(_VALID_VOCAB)
            vocab["verbs"][0]["type"] = vtype
            errors = validate_vocab_schema(vocab)
            type_errors = [e for e in errors if "type" in e and vtype not in e]
            assert not type_errors, f"Valid type {vtype!r} was rejected: {errors}"

    def test_multiple_errors_reported_together(self):
        errors = validate_vocab_schema({"nouns": [], "verbs": []})
        assert len(errors) >= 2


# ── generate_vocab ────────────────────────────────────────────────────────────

class TestGenerateVocab:
    """Mocks ask_llm_json_free so no LLM server is required."""

    def test_returns_valid_vocab_dict(self, tmp_path):
        with patch("jlesson.vocab_generator.ask_llm_json_free", return_value=_vocab()) as _:
            result = generate_vocab("test", save=False)
        assert result["theme"] == "test"
        assert len(result["nouns"]) == 2
        assert len(result["verbs"]) == 1

    def test_saves_file_when_save_true(self, tmp_path):
        with patch("jlesson.vocab_generator.ask_llm_json_free", return_value=_vocab()):
            generate_vocab("testtheme", save=True, output_dir=tmp_path)
        assert (tmp_path / "testtheme.json").exists()

    def test_saved_file_content_matches_returned_dict(self, tmp_path):
        import json
        with patch("jlesson.vocab_generator.ask_llm_json_free", return_value=_vocab()):
            result = generate_vocab("testtheme", save=True, output_dir=tmp_path)
        saved = json.loads((tmp_path / "testtheme.json").read_text(encoding="utf-8"))
        assert saved["theme"] == result["theme"]
        assert len(saved["nouns"]) == len(result["nouns"])

    def test_no_file_written_when_save_false(self, tmp_path):
        with patch("jlesson.vocab_generator.ask_llm_json_free", return_value=_vocab()):
            generate_vocab("testtheme", save=False, output_dir=tmp_path)
        assert not (tmp_path / "testtheme.json").exists()

    def test_theme_injected_if_missing_from_llm_response(self, tmp_path):
        """LLM sometimes omits the 'theme' key — generate_vocab should inject it."""
        vocab_without_theme = _vocab()
        del vocab_without_theme["theme"]
        with patch("jlesson.vocab_generator.ask_llm_json_free", return_value=vocab_without_theme):
            result = generate_vocab("animals", save=False)
        assert result["theme"] == "animals"

    def test_raises_value_error_on_schema_validation_failure(self):
        bad_response = {"theme": "bad", "nouns": "not-a-list", "verbs": []}
        with patch("jlesson.vocab_generator.ask_llm_json_free", return_value=bad_response):
            with pytest.raises(ValueError, match="schema validation"):
                generate_vocab("bad", save=False)

    def test_llm_uses_correct_theme_in_prompt(self):
        """Ask_llm_json_free should be called with a prompt mentioning the theme."""
        with patch("jlesson.vocab_generator.ask_llm_json_free", return_value=_vocab()) as mock_llm:
            generate_vocab("animals", save=False)
        call_args = mock_llm.call_args[0][0]
        assert "animals" in call_args

    def test_llm_uses_correct_num_nouns_and_verbs_in_prompt(self):
        with patch("jlesson.vocab_generator.ask_llm_json_free", return_value=_vocab()) as mock_llm:
            generate_vocab("animals", num_nouns=8, num_verbs=5, save=False)
        call_args = mock_llm.call_args[0][0]
        assert "8" in call_args
        assert "5" in call_args

    def test_creates_output_directory_if_missing(self, tmp_path):
        nested = tmp_path / "deep" / "nested"
        with patch("jlesson.vocab_generator.ask_llm_json_free", return_value=_vocab()):
            generate_vocab("testtheme", save=True, output_dir=nested)
        assert (nested / "testtheme.json").exists()
