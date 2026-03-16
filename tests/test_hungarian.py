"""
Unit tests for Hungarian-English language pair support.

Covers:
  - LanguageConfig registry — get_language_config("hun-eng")
  - HUN_TO_ENG_GRAMMAR_PROGRESSION table integrity (fields, unique IDs, prerequisites, no cycles)
  - Hungarian vocab schema validation
  - Hungarian prompt template functions return non-empty strings
  - get_next_grammar_from() with Hungarian progression
  - LessonConfig language field default and override
  - _resolve_output_dir() returns correct subfolder for hun-eng
  - LessonContent.language round-trips through JSON
"""

import json
from pathlib import Path

import pytest

from jlesson.curriculum import HUN_TO_ENG_GRAMMAR_PROGRESSION, get_next_grammar_from
from jlesson.language_config import HUN_ENG_CONFIG, get_language_config
from jlesson.lesson_pipeline import LessonConfig, LessonContext, _resolve_output_dir
from jlesson.models import LessonContent
from jlesson.prompt_template import (
    HUNGARIAN_PERSONS,
    hungarian_build_grammar_generate_prompt,
    hungarian_build_grammar_select_prompt,
    hungarian_build_noun_practice_prompt,
    hungarian_build_sentence_review_prompt,
    hungarian_build_verb_practice_prompt,
    hungarian_build_vocab_prompt,
)
from jlesson.vocab_generator import validate_hungarian_vocab_schema


# ─── Helpers ─────────────────────────────────────────────────────────────────

_HUN_NOUN = lambda en: {"english": en, "hungarian": f"{en}_hu", "pronunciation": f"/{en}/"}
_HUN_VERB = lambda en: {
    "english": en,
    "hungarian": f"{en}_hu",
    "pronunciation": f"/{en}/",
    "past_tense": f"{en}ed",
}

_HUN_GRAMMAR_IDS = {g["id"] for g in HUN_TO_ENG_GRAMMAR_PROGRESSION}


# ─── LanguageConfig registry ─────────────────────────────────────────────────

class TestLanguageConfigHunEng:
    def test_get_language_config_returns_hun_eng(self):
        cfg = get_language_config("hun-eng")
        assert cfg is HUN_ENG_CONFIG

    def test_code_is_hun_eng(self):
        assert HUN_ENG_CONFIG.code == "hun-eng"

    def test_target_language_is_english(self):
        assert HUN_ENG_CONFIG.target_language == "English"

    def test_native_language_is_hungarian(self):
        assert HUN_ENG_CONFIG.native_language == "Hungarian"

    def test_vocab_dir_is_hungarian_subfolder(self):
        assert HUN_ENG_CONFIG.vocab_dir == "vocab/hungarian"

    def test_curriculum_file_is_hungarian(self):
        assert "hungarian" in HUN_ENG_CONFIG.curriculum_file

    def test_has_hungarian_voices(self):
        assert "hungarian_female" in HUN_ENG_CONFIG.voices
        assert "hungarian_male" in HUN_ENG_CONFIG.voices

    def test_hungarian_female_voice_is_noemi(self):
        assert HUN_ENG_CONFIG.voices["hungarian_female"] == "hu-HU-NoemiNeural"

    def test_hungarian_male_voice_is_tamas(self):
        assert HUN_ENG_CONFIG.voices["hungarian_male"] == "hu-HU-TamasNeural"

    def test_grammar_progression_is_non_empty(self):
        assert len(HUN_ENG_CONFIG.grammar_progression) > 0

    def test_persons_are_non_empty(self):
        assert len(HUN_ENG_CONFIG.persons) > 0

    def test_noun_fields_include_hungarian(self):
        assert "hungarian" in HUN_ENG_CONFIG.vocab_noun_fields

    def test_verb_fields_include_past_tense(self):
        assert "past_tense" in HUN_ENG_CONFIG.vocab_verb_fields

    def test_config_is_frozen(self):
        with pytest.raises((AttributeError, TypeError)):
            HUN_ENG_CONFIG.code = "changed"  # type: ignore[misc]

    def test_unknown_code_raises_value_error(self):
        with pytest.raises(ValueError, match="hun"):
            get_language_config("xx-yy")


# ─── HUN_TO_ENG Grammar Progression table integrity ─────────────────────────

class TestHunGrammarProgressionTable:
    _REQUIRED = {"id", "pattern", "description", "example_en", "example_hu", "requires", "level"}

    def test_all_required_fields_present(self):
        missing = [
            g["id"]
            for g in HUN_TO_ENG_GRAMMAR_PROGRESSION
            if not self._REQUIRED.issubset(g.keys())
        ]
        assert missing == [], f"Entries missing required fields: {missing}"

    def test_ids_are_unique(self):
        ids = [g["id"] for g in HUN_TO_ENG_GRAMMAR_PROGRESSION]
        assert len(ids) == len(set(ids)), "Duplicate grammar IDs found"

    def test_at_least_26_entries(self):
        assert len(HUN_TO_ENG_GRAMMAR_PROGRESSION) >= 26

    def test_all_prerequisite_ids_exist(self):
        bad = [
            f"{g['id']} requires unknown {req!r}"
            for g in HUN_TO_ENG_GRAMMAR_PROGRESSION
            for req in g["requires"]
            if req not in _HUN_GRAMMAR_IDS
        ]
        assert bad == [], f"Unknown prerequisite IDs: {bad}"

    def test_no_self_referential_prerequisites(self):
        bad = [g["id"] for g in HUN_TO_ENG_GRAMMAR_PROGRESSION if g["id"] in g["requires"]]
        assert bad == [], f"Self-referential prerequisites: {bad}"

    def test_level_1_steps_have_no_prerequisites(self):
        bad = [
            g["id"]
            for g in HUN_TO_ENG_GRAMMAR_PROGRESSION
            if g["level"] == 1 and g["requires"]
        ]
        assert bad == [], f"Level-1 steps should have no prerequisites: {bad}"

    def test_at_least_one_step_per_level(self):
        levels = {g["level"] for g in HUN_TO_ENG_GRAMMAR_PROGRESSION}
        for lvl in range(1, max(levels) + 1):
            assert lvl in levels, f"No grammar step at level {lvl}"

    def test_no_cycles(self):
        """Topological sort must succeed (no cycles in the DAG)."""
        id_to_entry = {g["id"]: g for g in HUN_TO_ENG_GRAMMAR_PROGRESSION}
        visited: set[str] = set()
        in_stack: set[str] = set()

        def dfs(gid: str) -> bool:
            if gid in in_stack:
                return True  # cycle detected
            if gid in visited:
                return False
            in_stack.add(gid)
            for req in id_to_entry.get(gid, {}).get("requires", []):
                if dfs(req):
                    return True
            in_stack.discard(gid)
            visited.add(gid)
            return False

        cycles = [g["id"] for g in HUN_TO_ENG_GRAMMAR_PROGRESSION if dfs(g["id"])]
        assert cycles == [], f"Cycles detected in grammar DAG: {cycles}"


# ─── Hungarian vocab schema validation ───────────────────────────────────────

class TestHunVocabSchema:
    def _valid(self):
        return {
            "theme": "food",
            "nouns": [_HUN_NOUN("bread"), _HUN_NOUN("milk")],
            "verbs": [_HUN_VERB("to eat"), _HUN_VERB("to drink")],
        }

    def test_valid_returns_no_errors(self):
        assert validate_hungarian_vocab_schema(self._valid()) == []

    def test_missing_theme_reports_error(self):
        v = self._valid()
        del v["theme"]
        errors = validate_hungarian_vocab_schema(v)
        assert any("theme" in e for e in errors)

    def test_empty_nouns_reports_error(self):
        v = self._valid()
        v["nouns"] = []
        errors = validate_hungarian_vocab_schema(v)
        assert errors

    def test_noun_missing_pronunciation_reports_error(self):
        v = self._valid()
        del v["nouns"][0]["pronunciation"]
        errors = validate_hungarian_vocab_schema(v)
        assert any("pronunciation" in e for e in errors)

    def test_verb_missing_past_tense_reports_error(self):
        v = self._valid()
        del v["verbs"][0]["past_tense"]
        errors = validate_hungarian_vocab_schema(v)
        assert any("past_tense" in e for e in errors)

    def test_food_json_file_is_valid(self):
        """The bundled food.json file for Hungarian must pass schema validation."""
        food_path = Path(__file__).parent.parent / "vocab" / "hungarian" / "food.json"
        assert food_path.exists(), "vocab/hungarian/food.json is missing"
        with open(food_path, encoding="utf-8") as fh:
            vocab = json.load(fh)
        errors = validate_hungarian_vocab_schema(vocab)
        assert errors == [], f"food.json schema errors: {errors}"


# ─── Hungarian prompt template functions ─────────────────────────────────────

class TestHungarianPrompts:
    _NOUNS = [_HUN_NOUN("bread"), _HUN_NOUN("milk"), _HUN_NOUN("water")]
    _VERBS = [_HUN_VERB("to eat"), _HUN_VERB("to drink")]
    _GRAMMAR = [HUN_TO_ENG_GRAMMAR_PROGRESSION[0]]  # first entry (level 1)

    def test_vocab_prompt_is_non_empty(self):
        assert hungarian_build_vocab_prompt("food")

    def test_vocab_prompt_contains_theme(self):
        prompt = hungarian_build_vocab_prompt("food")
        assert "food" in prompt

    def test_vocab_prompt_contains_json_skeleton(self):
        prompt = hungarian_build_vocab_prompt("food")
        assert "nouns" in prompt and "verbs" in prompt

    def test_noun_practice_prompt_is_non_empty(self):
        assert hungarian_build_noun_practice_prompt(self._NOUNS)

    def test_noun_practice_prompt_contains_noun_english(self):
        prompt = hungarian_build_noun_practice_prompt(self._NOUNS)
        assert "bread" in prompt

    def test_verb_practice_prompt_is_non_empty(self):
        assert hungarian_build_verb_practice_prompt(self._VERBS)

    def test_verb_practice_prompt_contains_verb_english(self):
        prompt = hungarian_build_verb_practice_prompt(self._VERBS)
        assert "to eat" in prompt

    def test_grammar_select_prompt_is_non_empty(self):
        assert hungarian_build_grammar_select_prompt(
            self._GRAMMAR, self._NOUNS, self._VERBS, lesson_number=1, covered_grammar_ids=[]
        )

    def test_grammar_select_prompt_contains_grammar_id(self):
        prompt = hungarian_build_grammar_select_prompt(
            self._GRAMMAR, self._NOUNS, self._VERBS, lesson_number=1, covered_grammar_ids=[]
        )
        assert self._GRAMMAR[0]["id"] in prompt

    def test_grammar_generate_prompt_is_non_empty(self):
        assert hungarian_build_grammar_generate_prompt(
            self._GRAMMAR, self._NOUNS, self._VERBS
        )

    def test_grammar_generate_prompt_contains_persons(self):
        prompt = hungarian_build_grammar_generate_prompt(
            self._GRAMMAR, self._NOUNS, self._VERBS
        )
        # At least one HUNGARIAN_PERSONS entry should appear
        found = any(p[0] in prompt or p[1] in prompt for p in HUNGARIAN_PERSONS)
        assert found, "Expected at least one person name in grammar-generate prompt"

    def test_sentence_review_prompt_is_non_empty(self):
        sentences = [
            {"english": "I eat bread.", "hungarian": "Kenyeret eszem."},
        ]
        assert hungarian_build_sentence_review_prompt(
            sentences, self._NOUNS, self._VERBS, self._GRAMMAR
        )


# ─── get_next_grammar_from with Hungarian progression ────────────────────────

class TestGetNextGrammarFromHun:
    def test_empty_covered_returns_level1_only(self):
        result = get_next_grammar_from(HUN_TO_ENG_GRAMMAR_PROGRESSION, [])
        assert all(g["level"] == 1 for g in result)

    def test_level1_results_are_sorted_first(self):
        result = get_next_grammar_from(HUN_TO_ENG_GRAMMAR_PROGRESSION, [])
        levels = [g["level"] for g in result]
        assert levels == sorted(levels)

    def test_covered_step_not_returned(self):
        covered = ["present_simple_affirmative"]
        result = get_next_grammar_from(HUN_TO_ENG_GRAMMAR_PROGRESSION, covered)
        ids = {g["id"] for g in result}
        assert "present_simple_affirmative" not in ids

    def test_completing_prereq_unlocks_dependent(self):
        # present_simple_negative requires present_simple_affirmative
        covered_before = []
        covered_after = ["present_simple_affirmative"]
        before_ids = {g["id"] for g in get_next_grammar_from(HUN_TO_ENG_GRAMMAR_PROGRESSION, covered_before)}
        after_ids = {g["id"] for g in get_next_grammar_from(HUN_TO_ENG_GRAMMAR_PROGRESSION, covered_after)}
        assert "present_simple_negative" not in before_ids
        assert "present_simple_negative" in after_ids

    def test_all_covered_returns_empty(self):
        all_ids = [g["id"] for g in HUN_TO_ENG_GRAMMAR_PROGRESSION]
        result = get_next_grammar_from(HUN_TO_ENG_GRAMMAR_PROGRESSION, all_ids)
        assert result == []


# ─── LessonConfig language field ─────────────────────────────────────────────

class TestLessonConfigLanguage:
    def test_default_language_is_eng_jap(self, tmp_path):
        cfg = LessonConfig(theme="food", curriculum_path=tmp_path / "c.json")
        assert cfg.language == "eng-jap"

    def test_language_can_be_set_to_hun_eng(self, tmp_path):
        cfg = LessonConfig(theme="food", curriculum_path=tmp_path / "c.json", language="hun-eng")
        assert cfg.language == "hun-eng"

    def test_context_post_init_populates_language_config(self, tmp_path):
        cfg = LessonConfig(theme="food", curriculum_path=tmp_path / "c.json", language="hun-eng")
        ctx = LessonContext(config=cfg)
        assert ctx.language_config is not None
        assert ctx.language_config.code == "hun-eng"

    def test_eng_jap_context_has_correct_language_config(self, tmp_path):
        cfg = LessonConfig(theme="food", curriculum_path=tmp_path / "c.json")
        ctx = LessonContext(config=cfg)
        assert ctx.language_config is not None
        assert ctx.language_config.code == "eng-jap"


# ─── _resolve_output_dir ─────────────────────────────────────────────────────

class TestResolveOutputDir:
    def test_eng_jap_returns_base_dir(self, tmp_path):
        cfg = LessonConfig(theme="food", curriculum_path=tmp_path / "c.json", output_dir=tmp_path)
        result = _resolve_output_dir(cfg)
        assert result == tmp_path

    def test_hun_eng_returns_hungarian_subfolder(self, tmp_path):
        cfg = LessonConfig(
            theme="food",
            curriculum_path=tmp_path / "c.json",
            output_dir=tmp_path,
            language="hun-eng",
        )
        result = _resolve_output_dir(cfg)
        assert result == tmp_path / "hungarian"

    def test_hun_eng_subfolder_name_is_lowercase_native_language(self, tmp_path):
        cfg = LessonConfig(
            theme="food",
            curriculum_path=tmp_path / "c.json",
            output_dir=tmp_path,
            language="hun-eng",
        )
        result = _resolve_output_dir(cfg)
        # native_language is "Hungarian" → subfolder should be "hungarian"
        assert result.name == "hungarian"

    def test_eng_jap_explicit_output_dir_preserved(self, tmp_path):
        custom = tmp_path / "custom_output"
        cfg = LessonConfig(theme="food", curriculum_path=tmp_path / "c.json", output_dir=custom)
        result = _resolve_output_dir(cfg)
        assert result == custom


# ─── LessonContent.language round-trip ───────────────────────────────────────

class TestLessonContentLanguageRoundtrip:
    def test_default_language_is_eng_jap(self):
        content = LessonContent(
            lesson_id=1,
            theme="food",
            nouns=[],
            verbs=[],
            sentences=[],
            noun_items=[],
            verb_items=[],
        )
        assert content.language == "eng-jap"

    def test_hun_eng_language_survives_json_roundtrip(self):
        content = LessonContent(
            lesson_id=1,
            theme="food",
            nouns=[],
            verbs=[],
            sentences=[],
            noun_items=[],
            verb_items=[],
            language="hun-eng",
        )
        data = content.model_dump()
        restored = LessonContent(**data)
        assert restored.language == "hun-eng"

    def test_json_serialization_preserves_language(self):
        content = LessonContent(
            lesson_id=2,
            theme="animals",
            nouns=[],
            verbs=[],
            sentences=[],
            noun_items=[],
            verb_items=[],
            language="hun-eng",
        )
        raw = json.loads(content.model_dump_json())
        assert raw["language"] == "hun-eng"
