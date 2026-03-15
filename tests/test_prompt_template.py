"""
Unit tests for prompt_template.py — new prompts only.

Covers the five JSON-output prompt builders added in the curriculum sprint:
  - build_noun_practice_prompt
  - build_verb_practice_prompt
  - build_grammar_select_prompt
  - build_grammar_generate_prompt
  - build_content_validate_prompt

Existing build_lesson_prompt / build_vocab_prompt are not re-tested here.
Each test asserts that the generated prompt string:
  1. Contains the critical input data (nouns/verbs/grammar IDs/persons)
  2. Contains the expected JSON skeleton / key names
  3. Has reasonable length (is not empty or excessively short)
"""

import pytest

from jlesson.curriculum import GRAMMAR_PROGRESSION
from jlesson.prompt_template import (
    build_content_validate_prompt,
    build_grammar_generate_prompt,
    build_grammar_select_prompt,
    build_noun_practice_prompt,
    build_verb_practice_prompt,
)

# ── Shared fixtures ───────────────────────────────────────────────────────────

@pytest.fixture
def sample_nouns():
    return [
        {"english": "water", "japanese": "みず", "kanji": "水", "romaji": "mizu"},
        {"english": "fish",  "japanese": "さかな", "kanji": "魚", "romaji": "sakana"},
    ]


@pytest.fixture
def sample_verbs():
    return [
        {
            "english": "to eat", "japanese": "たべる", "kanji": "食べる",
            "romaji": "taberu", "type": "る-verb", "masu_form": "食べます",
        },
        {
            "english": "to drink", "japanese": "のむ", "kanji": "飲む",
            "romaji": "nomu", "type": "う-verb", "masu_form": "飲みます",
        },
    ]


@pytest.fixture
def level1_grammar():
    return [g for g in GRAMMAR_PROGRESSION if g["level"] == 1]


@pytest.fixture
def sample_sentences():
    return [
        {"english": "I eat fish.", "japanese": "私は魚を食べます。", "romaji": "Watashi wa sakana o tabemasu."},
        {"english": "You drink water.", "japanese": "あなたは水を飲みます。", "romaji": "Anata wa mizu o nomimasu."},
    ]


# ── build_noun_practice_prompt ────────────────────────────────────────────────

class TestBuildNounPracticePrompt:
    def test_returns_non_empty_string(self, sample_nouns):
        prompt = build_noun_practice_prompt(sample_nouns)
        assert isinstance(prompt, str)
        assert len(prompt) > 100

    def test_contains_each_noun_english(self, sample_nouns):
        prompt = build_noun_practice_prompt(sample_nouns)
        for noun in sample_nouns:
            assert noun["english"] in prompt

    def test_contains_each_noun_kanji(self, sample_nouns):
        prompt = build_noun_practice_prompt(sample_nouns)
        for noun in sample_nouns:
            assert noun["kanji"] in prompt

    def test_contains_lesson_number(self, sample_nouns):
        prompt = build_noun_practice_prompt(sample_nouns, lesson_number=5)
        assert "5" in prompt

    def test_json_skeleton_has_noun_items_key(self, sample_nouns):
        prompt = build_noun_practice_prompt(sample_nouns)
        assert "noun_items" in prompt

    def test_json_skeleton_has_memory_tip_key(self, sample_nouns):
        prompt = build_noun_practice_prompt(sample_nouns)
        assert "memory_tip" in prompt

    def test_json_skeleton_has_example_sentence_keys(self, sample_nouns):
        prompt = build_noun_practice_prompt(sample_nouns)
        assert "example_sentence_jp" in prompt
        assert "example_sentence_en" in prompt


# ── build_verb_practice_prompt ────────────────────────────────────────────────

class TestBuildVerbPracticePrompt:
    def test_returns_non_empty_string(self, sample_verbs):
        prompt = build_verb_practice_prompt(sample_verbs)
        assert isinstance(prompt, str)
        assert len(prompt) > 100

    def test_contains_each_verb_english(self, sample_verbs):
        prompt = build_verb_practice_prompt(sample_verbs)
        for verb in sample_verbs:
            assert verb["english"] in prompt

    def test_contains_each_verb_masu_form(self, sample_verbs):
        prompt = build_verb_practice_prompt(sample_verbs)
        for verb in sample_verbs:
            assert verb["masu_form"] in prompt

    def test_json_skeleton_has_verb_items_key(self, sample_verbs):
        prompt = build_verb_practice_prompt(sample_verbs)
        assert "verb_items" in prompt

    def test_json_skeleton_has_all_four_polite_form_keys(self, sample_verbs):
        prompt = build_verb_practice_prompt(sample_verbs)
        for key in ("present_aff", "present_neg", "past_aff", "past_neg"):
            assert key in prompt

    def test_json_skeleton_has_polite_forms_wrapper_key(self, sample_verbs):
        prompt = build_verb_practice_prompt(sample_verbs)
        assert "polite_forms" in prompt

    def test_contains_lesson_number(self, sample_verbs):
        prompt = build_verb_practice_prompt(sample_verbs, lesson_number=3)
        assert "3" in prompt


# ── build_grammar_select_prompt ───────────────────────────────────────────────

class TestBuildGrammarSelectPrompt:
    def test_returns_non_empty_string(self, level1_grammar, sample_nouns, sample_verbs):
        prompt = build_grammar_select_prompt(
            unlocked_grammar=level1_grammar,
            available_nouns=sample_nouns,
            available_verbs=sample_verbs,
            lesson_number=1,
            covered_grammar_ids=[],
        )
        assert isinstance(prompt, str)
        assert len(prompt) > 100

    def test_contains_grammar_ids(self, level1_grammar, sample_nouns, sample_verbs):
        prompt = build_grammar_select_prompt(
            unlocked_grammar=level1_grammar,
            available_nouns=sample_nouns,
            available_verbs=sample_verbs,
            lesson_number=1,
            covered_grammar_ids=[],
        )
        for g in level1_grammar:
            assert g["id"] in prompt

    def test_contains_noun_names(self, level1_grammar, sample_nouns, sample_verbs):
        prompt = build_grammar_select_prompt(
            unlocked_grammar=level1_grammar,
            available_nouns=sample_nouns,
            available_verbs=sample_verbs,
            lesson_number=1,
            covered_grammar_ids=[],
        )
        for noun in sample_nouns:
            assert noun["english"] in prompt

    def test_contains_verb_names(self, level1_grammar, sample_nouns, sample_verbs):
        prompt = build_grammar_select_prompt(
            unlocked_grammar=level1_grammar,
            available_nouns=sample_nouns,
            available_verbs=sample_verbs,
            lesson_number=1,
            covered_grammar_ids=[],
        )
        for verb in sample_verbs:
            assert verb["english"] in prompt

    def test_shows_covered_grammar_ids(self, level1_grammar, sample_nouns, sample_verbs):
        prompt = build_grammar_select_prompt(
            unlocked_grammar=level1_grammar,
            available_nouns=sample_nouns,
            available_verbs=sample_verbs,
            lesson_number=2,
            covered_grammar_ids=["action_present_affirmative"],
        )
        assert "action_present_affirmative" in prompt

    def test_shows_none_when_no_covered_grammar(self, level1_grammar, sample_nouns, sample_verbs):
        prompt = build_grammar_select_prompt(
            unlocked_grammar=level1_grammar,
            available_nouns=sample_nouns,
            available_verbs=sample_verbs,
            lesson_number=1,
            covered_grammar_ids=[],
        )
        assert "(none)" in prompt

    def test_json_skeleton_has_selected_ids_key(self, level1_grammar, sample_nouns, sample_verbs):
        prompt = build_grammar_select_prompt(
            unlocked_grammar=level1_grammar,
            available_nouns=sample_nouns,
            available_verbs=sample_verbs,
            lesson_number=1,
            covered_grammar_ids=[],
        )
        assert "selected_ids" in prompt
        assert "rationale" in prompt


# ── build_grammar_generate_prompt ─────────────────────────────────────────────

class TestBuildGrammarGeneratePrompt:
    def test_returns_non_empty_string(self, level1_grammar, sample_nouns, sample_verbs):
        prompt = build_grammar_generate_prompt(
            grammar_specs=level1_grammar[:1],
            nouns=sample_nouns,
            verbs=sample_verbs,
        )
        assert isinstance(prompt, str)
        assert len(prompt) > 100

    def test_contains_grammar_structure(self, level1_grammar, sample_nouns, sample_verbs):
        prompt = build_grammar_generate_prompt(
            grammar_specs=level1_grammar[:1],
            nouns=sample_nouns,
            verbs=sample_verbs,
        )
        assert level1_grammar[0]["structure"] in prompt

    def test_contains_noun_kanji(self, level1_grammar, sample_nouns, sample_verbs):
        prompt = build_grammar_generate_prompt(
            grammar_specs=level1_grammar[:1],
            nouns=sample_nouns,
            verbs=sample_verbs,
        )
        for noun in sample_nouns:
            assert noun["kanji"] in prompt

    def test_contains_person_names(self, level1_grammar, sample_nouns, sample_verbs):
        persons = [("I", "私", "watashi"), ("You", "あなた", "anata")]
        prompt = build_grammar_generate_prompt(
            grammar_specs=level1_grammar[:1],
            nouns=sample_nouns,
            verbs=sample_verbs,
            persons=persons,
        )
        assert "watashi" in prompt
        assert "anata" in prompt

    def test_default_persons_included(self, level1_grammar, sample_nouns, sample_verbs):
        prompt = build_grammar_generate_prompt(
            grammar_specs=level1_grammar[:1],
            nouns=sample_nouns,
            verbs=sample_verbs,
        )
        assert "watashi" in prompt or "I" in prompt

    def test_json_skeleton_has_sentences_key(self, level1_grammar, sample_nouns, sample_verbs):
        prompt = build_grammar_generate_prompt(
            grammar_specs=level1_grammar[:1],
            nouns=sample_nouns,
            verbs=sample_verbs,
        )
        assert '"sentences"' in prompt

    def test_json_skeleton_has_grammar_id_and_notes_keys(self, level1_grammar, sample_nouns, sample_verbs):
        prompt = build_grammar_generate_prompt(
            grammar_specs=level1_grammar[:1],
            nouns=sample_nouns,
            verbs=sample_verbs,
        )
        assert "grammar_id" in prompt
        assert "notes" in prompt

    def test_total_sentence_count_in_prompt(self, level1_grammar, sample_nouns, sample_verbs):
        """The prompt should mention the total expected sentence count."""
        prompt = build_grammar_generate_prompt(
            grammar_specs=level1_grammar[:2],
            nouns=sample_nouns,
            verbs=sample_verbs,
            sentences_per_grammar=3,
        )
        # 2 grammar specs × 3 sentences = 6 total
        assert "6" in prompt


# ── build_content_validate_prompt ─────────────────────────────────────────────

class TestBuildContentValidatePrompt:
    def test_returns_non_empty_string(self, sample_sentences):
        prompt = build_content_validate_prompt(sample_sentences)
        assert isinstance(prompt, str)
        assert len(prompt) > 100

    def test_contains_each_sentence_japanese(self, sample_sentences):
        prompt = build_content_validate_prompt(sample_sentences)
        for s in sample_sentences:
            assert s["japanese"] in prompt

    def test_contains_each_sentence_english(self, sample_sentences):
        prompt = build_content_validate_prompt(sample_sentences)
        for s in sample_sentences:
            assert s["english"] in prompt

    def test_contains_each_sentence_romaji(self, sample_sentences):
        prompt = build_content_validate_prompt(sample_sentences)
        for s in sample_sentences:
            assert s["romaji"] in prompt

    def test_uses_zero_based_indices(self, sample_sentences):
        prompt = build_content_validate_prompt(sample_sentences)
        assert "[0]" in prompt
        assert "[1]" in prompt

    def test_json_skeleton_has_score_key(self, sample_sentences):
        prompt = build_content_validate_prompt(sample_sentences)
        assert '"score"' in prompt

    def test_json_skeleton_has_corrections_key(self, sample_sentences):
        prompt = build_content_validate_prompt(sample_sentences)
        assert '"corrections"' in prompt

    def test_json_skeleton_has_severity_key(self, sample_sentences):
        prompt = build_content_validate_prompt(sample_sentences)
        assert "severity" in prompt

    def test_json_skeleton_has_summary_key(self, sample_sentences):
        prompt = build_content_validate_prompt(sample_sentences)
        assert '"summary"' in prompt

    def test_works_with_empty_sentence_list(self):
        prompt = build_content_validate_prompt([])
        assert isinstance(prompt, str)
        assert len(prompt) > 50
