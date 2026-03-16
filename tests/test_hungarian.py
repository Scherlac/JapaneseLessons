"""
Unit tests for Hungarian-English language pair support.

Covers:
  - HungarianNounItem / HungarianVerbItem  — field creation and validation
  - vocab/hungarian/*.json                 — all files are valid JSON with correct fields
  - Hungarian prompt functions             — each returns a non-empty string
  - HUN_TO_ENG_GRAMMAR_PROGRESSION        — fields, unique IDs, prerequisite integrity
  - Hungarian LanguageConfig              — all required fields present and correct
"""

import json
from pathlib import Path

import pytest

from jlesson.curriculum import HUN_TO_ENG_GRAMMAR_PROGRESSION, get_next_grammar_from
from jlesson.language_config import HUN_ENG_CONFIG, get_language_config
from jlesson.models import (
    HungarianNounItem,
    HungarianSentence,
    HungarianVerbItem,
)
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

# ── Paths ─────────────────────────────────────────────────────────────────────

_VOCAB_HUN_DIR = Path(__file__).parent.parent / "vocab" / "hungarian"
_HUN_VOCAB_FILES = sorted(_VOCAB_HUN_DIR.glob("*.json"))

# ── Shared test data ──────────────────────────────────────────────────────────

_NOUNS = [
    {"english": "bread",  "hungarian": "kenyér",  "pronunciation": "bred"},
    {"english": "milk",   "hungarian": "tej",     "pronunciation": "mɪlk"},
    {"english": "water",  "hungarian": "víz",     "pronunciation": "ˈwɔːtər"},
]
_VERBS = [
    {"english": "to eat",   "hungarian": "enni",  "pronunciation": "tuː iːt",   "past_tense": "ate"},
    {"english": "to drink", "hungarian": "inni",  "pronunciation": "tuː drɪŋk", "past_tense": "drank"},
]
_GRAMMAR_L1 = [g for g in HUN_TO_ENG_GRAMMAR_PROGRESSION if g["level"] == 1]
_ALL_IDS = {g["id"] for g in HUN_TO_ENG_GRAMMAR_PROGRESSION}


# ─────────────────────────────────────────────────────────────────────────────
# HungarianNounItem
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestHungarianNounItem:
    def test_create_with_all_fields(self):
        item = HungarianNounItem(
            english="bread",
            hungarian="kenyér",
            pronunciation="bred",
            example_sentence_en="I eat bread.",
            example_sentence_hu="Kenyeret eszem.",
            memory_tip="Like 'bready'",
        )
        assert item.english == "bread"
        assert item.hungarian == "kenyér"
        assert item.pronunciation == "bred"
        assert item.example_sentence_en == "I eat bread."
        assert item.example_sentence_hu == "Kenyeret eszem."
        assert item.memory_tip == "Like 'bready'"

    def test_create_with_required_fields_only(self):
        item = HungarianNounItem(english="cat", hungarian="macska", pronunciation="kæt")
        assert item.english == "cat"
        assert item.hungarian == "macska"
        assert item.pronunciation == "kæt"

    def test_defaults_are_empty_strings(self):
        item = HungarianNounItem()
        assert item.english == ""
        assert item.hungarian == ""
        assert item.pronunciation == ""
        assert item.example_sentence_en == ""
        assert item.example_sentence_hu == ""
        assert item.memory_tip == ""

    def test_model_dump_contains_all_fields(self):
        item = HungarianNounItem(english="dog", hungarian="kutya", pronunciation="dɒɡ")
        data = item.model_dump()
        assert "english" in data
        assert "hungarian" in data
        assert "pronunciation" in data
        assert "example_sentence_en" in data
        assert "example_sentence_hu" in data
        assert "memory_tip" in data

    def test_round_trip_via_model_dump(self):
        original = HungarianNounItem(
            english="apple", hungarian="alma", pronunciation="ˈæpəl",
            memory_tip="Sounds like 'apple'",
        )
        restored = HungarianNounItem(**original.model_dump())
        assert restored == original


# ─────────────────────────────────────────────────────────────────────────────
# HungarianVerbItem
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestHungarianVerbItem:
    def test_create_with_all_fields(self):
        item = HungarianVerbItem(
            english="to eat",
            hungarian="enni",
            pronunciation="tuː iːt",
            past_tense="ate",
            example_sentence_en="She ate the cake.",
            example_sentence_hu="Ő megette a tortát.",
            memory_tip="Irregular: eat → ate",
        )
        assert item.english == "to eat"
        assert item.hungarian == "enni"
        assert item.pronunciation == "tuː iːt"
        assert item.past_tense == "ate"
        assert item.example_sentence_en == "She ate the cake."
        assert item.example_sentence_hu == "Ő megette a tortát."
        assert item.memory_tip == "Irregular: eat → ate"

    def test_create_with_required_fields_only(self):
        item = HungarianVerbItem(
            english="to run", hungarian="futni", pronunciation="tuː rʌn", past_tense="ran"
        )
        assert item.english == "to run"
        assert item.past_tense == "ran"

    def test_defaults_are_empty_strings(self):
        item = HungarianVerbItem()
        assert item.english == ""
        assert item.hungarian == ""
        assert item.pronunciation == ""
        assert item.past_tense == ""
        assert item.example_sentence_en == ""
        assert item.example_sentence_hu == ""
        assert item.memory_tip == ""

    def test_model_dump_contains_past_tense(self):
        item = HungarianVerbItem(english="to go", hungarian="menni", pronunciation="tuː ɡəʊ", past_tense="went")
        assert item.model_dump()["past_tense"] == "went"

    def test_round_trip_via_model_dump(self):
        original = HungarianVerbItem(
            english="to see", hungarian="látni", pronunciation="tuː siː", past_tense="saw"
        )
        restored = HungarianVerbItem(**original.model_dump())
        assert restored == original


# ─────────────────────────────────────────────────────────────────────────────
# Hungarian vocab files — JSON validity and field correctness
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestHungarianVocabFiles:
    """Each file in vocab/hungarian/ must be valid JSON satisfying the schema."""

    def test_vocab_directory_exists(self):
        assert _VOCAB_HUN_DIR.is_dir(), "vocab/hungarian/ directory is missing"

    def test_at_least_one_vocab_file_exists(self):
        assert len(_HUN_VOCAB_FILES) > 0, "No .json files found in vocab/hungarian/"

    @pytest.mark.parametrize("vocab_file", _HUN_VOCAB_FILES, ids=lambda p: p.name)
    def test_file_is_valid_json(self, vocab_file):
        with open(vocab_file, encoding="utf-8") as fh:
            data = json.load(fh)
        assert isinstance(data, dict)

    @pytest.mark.parametrize("vocab_file", _HUN_VOCAB_FILES, ids=lambda p: p.name)
    def test_file_has_theme_field(self, vocab_file):
        with open(vocab_file, encoding="utf-8") as fh:
            data = json.load(fh)
        assert "theme" in data, f"{vocab_file.name}: missing 'theme' field"

    @pytest.mark.parametrize("vocab_file", _HUN_VOCAB_FILES, ids=lambda p: p.name)
    def test_file_has_non_empty_nouns(self, vocab_file):
        with open(vocab_file, encoding="utf-8") as fh:
            data = json.load(fh)
        assert isinstance(data.get("nouns"), list) and len(data["nouns"]) > 0, \
            f"{vocab_file.name}: 'nouns' must be a non-empty list"

    @pytest.mark.parametrize("vocab_file", _HUN_VOCAB_FILES, ids=lambda p: p.name)
    def test_file_has_non_empty_verbs(self, vocab_file):
        with open(vocab_file, encoding="utf-8") as fh:
            data = json.load(fh)
        assert isinstance(data.get("verbs"), list) and len(data["verbs"]) > 0, \
            f"{vocab_file.name}: 'verbs' must be a non-empty list"

    @pytest.mark.parametrize("vocab_file", _HUN_VOCAB_FILES, ids=lambda p: p.name)
    def test_nouns_have_required_fields(self, vocab_file):
        required = {"english", "hungarian", "pronunciation"}
        with open(vocab_file, encoding="utf-8") as fh:
            data = json.load(fh)
        bad = [
            f"nouns[{i}] {n.get('english', '?')!r}: missing {sorted(required - n.keys())}"
            for i, n in enumerate(data.get("nouns", []))
            if not required.issubset(n.keys())
        ]
        assert bad == [], f"{vocab_file.name}: {bad}"

    @pytest.mark.parametrize("vocab_file", _HUN_VOCAB_FILES, ids=lambda p: p.name)
    def test_verbs_have_required_fields(self, vocab_file):
        required = {"english", "hungarian", "pronunciation", "past_tense"}
        with open(vocab_file, encoding="utf-8") as fh:
            data = json.load(fh)
        bad = [
            f"verbs[{i}] {v.get('english', '?')!r}: missing {sorted(required - v.keys())}"
            for i, v in enumerate(data.get("verbs", []))
            if not required.issubset(v.keys())
        ]
        assert bad == [], f"{vocab_file.name}: {bad}"

    @pytest.mark.parametrize("vocab_file", _HUN_VOCAB_FILES, ids=lambda p: p.name)
    def test_schema_validator_passes(self, vocab_file):
        with open(vocab_file, encoding="utf-8") as fh:
            data = json.load(fh)
        errors = validate_hungarian_vocab_schema(data)
        assert errors == [], f"{vocab_file.name}: schema errors: {errors}"


# ─────────────────────────────────────────────────────────────────────────────
# Hungarian prompt functions
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestHungarianPromptFunctions:
    def test_vocab_prompt_returns_non_empty_string(self):
        result = hungarian_build_vocab_prompt("food")
        assert isinstance(result, str) and result.strip()

    def test_vocab_prompt_contains_theme(self):
        assert "food" in hungarian_build_vocab_prompt("food")

    def test_vocab_prompt_contains_json_skeleton(self):
        prompt = hungarian_build_vocab_prompt("food")
        assert "nouns" in prompt
        assert "verbs" in prompt

    def test_noun_practice_prompt_returns_non_empty_string(self):
        result = hungarian_build_noun_practice_prompt(_NOUNS)
        assert isinstance(result, str) and result.strip()

    def test_noun_practice_prompt_contains_each_noun(self):
        prompt = hungarian_build_noun_practice_prompt(_NOUNS)
        for noun in _NOUNS:
            assert noun["english"] in prompt

    def test_verb_practice_prompt_returns_non_empty_string(self):
        result = hungarian_build_verb_practice_prompt(_VERBS)
        assert isinstance(result, str) and result.strip()

    def test_verb_practice_prompt_contains_each_verb(self):
        prompt = hungarian_build_verb_practice_prompt(_VERBS)
        for verb in _VERBS:
            assert verb["english"] in prompt

    def test_grammar_select_prompt_returns_non_empty_string(self):
        result = hungarian_build_grammar_select_prompt(
            _GRAMMAR_L1, _NOUNS, _VERBS, lesson_number=1, covered_grammar_ids=[]
        )
        assert isinstance(result, str) and result.strip()

    def test_grammar_select_prompt_contains_grammar_id(self):
        prompt = hungarian_build_grammar_select_prompt(
            _GRAMMAR_L1, _NOUNS, _VERBS, lesson_number=1, covered_grammar_ids=[]
        )
        for g in _GRAMMAR_L1:
            assert g["id"] in prompt

    def test_grammar_generate_prompt_returns_non_empty_string(self):
        result = hungarian_build_grammar_generate_prompt(_GRAMMAR_L1, _NOUNS, _VERBS)
        assert isinstance(result, str) and result.strip()

    def test_grammar_generate_prompt_contains_person_names(self):
        prompt = hungarian_build_grammar_generate_prompt(_GRAMMAR_L1, _NOUNS, _VERBS)
        assert any(p[0] in prompt or p[1] in prompt for p in HUNGARIAN_PERSONS)

    def test_sentence_review_prompt_returns_non_empty_string(self):
        sentences = [
            {"english": "I eat bread.", "hungarian": "Kenyeret eszem.", "grammar_id": "present_simple_affirmative"},
        ]
        result = hungarian_build_sentence_review_prompt(sentences, _NOUNS, _VERBS, _GRAMMAR_L1)
        assert isinstance(result, str) and result.strip()


# ─────────────────────────────────────────────────────────────────────────────
# HUN_TO_ENG_GRAMMAR_PROGRESSION table integrity
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestHunGrammarProgression:
    _REQUIRED_FIELDS = {"id", "pattern", "description", "example_en", "example_hu", "requires", "level"}

    def test_progression_is_non_empty(self):
        assert len(HUN_TO_ENG_GRAMMAR_PROGRESSION) > 0

    def test_all_required_fields_present(self):
        missing = [
            g["id"]
            for g in HUN_TO_ENG_GRAMMAR_PROGRESSION
            if not self._REQUIRED_FIELDS.issubset(g.keys())
        ]
        assert missing == [], f"Entries missing required fields: {missing}"

    def test_ids_are_unique(self):
        ids = [g["id"] for g in HUN_TO_ENG_GRAMMAR_PROGRESSION]
        assert len(ids) == len(set(ids)), "Duplicate grammar IDs detected"

    def test_all_prerequisite_ids_exist(self):
        bad = [
            f"{g['id']} → unknown prereq {req!r}"
            for g in HUN_TO_ENG_GRAMMAR_PROGRESSION
            for req in g["requires"]
            if req not in _ALL_IDS
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
        assert bad == [], f"Level-1 steps must have empty 'requires': {bad}"

    def test_at_least_one_step_per_level(self):
        levels = {g["level"] for g in HUN_TO_ENG_GRAMMAR_PROGRESSION}
        for lvl in range(1, max(levels) + 1):
            assert lvl in levels, f"No grammar step defined for level {lvl}"

    def test_no_cycles_in_dag(self):
        """Topological reachability — no node can be its own ancestor."""
        edges: dict[str, list[str]] = {g["id"]: list(g["requires"]) for g in HUN_TO_ENG_GRAMMAR_PROGRESSION}
        visited: set[str] = set()
        stack: set[str] = set()

        def has_cycle(node: str) -> bool:
            if node in stack:
                return True
            if node in visited:
                return False
            stack.add(node)
            for neighbour in edges.get(node, []):
                if has_cycle(neighbour):
                    return True
            stack.discard(node)
            visited.add(node)
            return False

        cycles = [g["id"] for g in HUN_TO_ENG_GRAMMAR_PROGRESSION if has_cycle(g["id"])]
        assert cycles == [], f"Cyclic prerequisites detected: {cycles}"

    def test_get_next_grammar_from_returns_level1_when_nothing_covered(self):
        result = get_next_grammar_from(HUN_TO_ENG_GRAMMAR_PROGRESSION, [])
        assert all(g["level"] == 1 for g in result)

    def test_covered_step_excluded_from_result(self):
        ids = {g["id"] for g in get_next_grammar_from(HUN_TO_ENG_GRAMMAR_PROGRESSION, ["present_simple_affirmative"])}
        assert "present_simple_affirmative" not in ids

    def test_completing_prereq_unlocks_dependent(self):
        before = {g["id"] for g in get_next_grammar_from(HUN_TO_ENG_GRAMMAR_PROGRESSION, [])}
        after = {g["id"] for g in get_next_grammar_from(HUN_TO_ENG_GRAMMAR_PROGRESSION, ["present_simple_affirmative"])}
        assert "present_simple_negative" not in before
        assert "present_simple_negative" in after

    def test_all_ids_covered_returns_empty(self):
        all_ids = [g["id"] for g in HUN_TO_ENG_GRAMMAR_PROGRESSION]
        assert get_next_grammar_from(HUN_TO_ENG_GRAMMAR_PROGRESSION, all_ids) == []


# ─────────────────────────────────────────────────────────────────────────────
# Hungarian LanguageConfig
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestHungarianLanguageConfig:
    def test_get_language_config_returns_hun_eng(self):
        assert get_language_config("hun-eng") is HUN_ENG_CONFIG

    def test_code_field(self):
        assert HUN_ENG_CONFIG.code == "hun-eng"

    def test_display_name_is_non_empty(self):
        assert HUN_ENG_CONFIG.display_name

    def test_target_language_is_english(self):
        assert HUN_ENG_CONFIG.target_language == "English"

    def test_native_language_is_hungarian(self):
        assert HUN_ENG_CONFIG.native_language == "Hungarian"

    def test_vocab_dir_points_to_hungarian_subfolder(self):
        assert HUN_ENG_CONFIG.vocab_dir == "vocab/hungarian"

    def test_curriculum_file_contains_hungarian(self):
        assert "hungarian" in HUN_ENG_CONFIG.curriculum_file

    def test_noun_fields_include_required_keys(self):
        for field in ("english", "hungarian", "pronunciation"):
            assert field in HUN_ENG_CONFIG.vocab_noun_fields, f"Missing noun field: {field}"

    def test_verb_fields_include_required_keys(self):
        for field in ("english", "hungarian", "pronunciation", "past_tense"):
            assert field in HUN_ENG_CONFIG.vocab_verb_fields, f"Missing verb field: {field}"

    def test_voices_has_hungarian_female(self):
        assert "hungarian_female" in HUN_ENG_CONFIG.voices

    def test_voices_has_hungarian_male(self):
        assert "hungarian_male" in HUN_ENG_CONFIG.voices

    def test_hungarian_female_voice_is_noemi(self):
        assert HUN_ENG_CONFIG.voices["hungarian_female"] == "hu-HU-NoemiNeural"

    def test_hungarian_male_voice_is_tamas(self):
        assert HUN_ENG_CONFIG.voices["hungarian_male"] == "hu-HU-TamasNeural"

    def test_grammar_progression_is_non_empty(self):
        assert len(HUN_ENG_CONFIG.grammar_progression) > 0

    def test_grammar_progression_matches_module_constant(self):
        assert list(HUN_ENG_CONFIG.grammar_progression) == HUN_TO_ENG_GRAMMAR_PROGRESSION

    def test_persons_is_non_empty(self):
        assert len(HUN_ENG_CONFIG.persons) > 0

    def test_config_is_frozen(self):
        with pytest.raises((AttributeError, TypeError)):
            HUN_ENG_CONFIG.code = "changed"  # type: ignore[misc]

    def test_unknown_code_raises_value_error(self):
        with pytest.raises(ValueError):
            get_language_config("xx-yy")

