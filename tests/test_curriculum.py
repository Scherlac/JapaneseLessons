"""
Unit tests for curriculum.py

Covers:
  - GRAMMAR_PROGRESSION table integrity (required fields, valid prerequisite IDs)
  - get_next_grammar  — prerequisite resolution across multiple states
  - create_curriculum — correct initial structure
  - add_lesson        — adds lesson, does NOT yet update covered trackers
  - complete_lesson   — updates covered_nouns / covered_verbs / covered_grammar_ids
  - suggest_new_vocab — fresh-first selection, fill-up from covered if too few fresh
  - summary           — smoke-test non-empty string output
  - load/save round-trip (tmp_path)
"""

import json
from pathlib import Path

import pytest

from curriculum import (
    GRAMMAR_PROGRESSION,
    add_lesson,
    complete_lesson,
    create_curriculum,
    get_grammar_by_id,
    get_next_grammar,
    load_curriculum,
    save_curriculum,
    suggest_new_vocab,
    summary,
)

# ─── Fixtures ────────────────────────────────────────────────────────────────

_NOUN = lambda en: {"english": en, "japanese": "x", "kanji": "X", "romaji": "x"}
_VERB = lambda en: {
    "english": en, "japanese": "x", "kanji": "X",
    "romaji": "x", "type": "る-verb", "masu_form": "Xます",
}


@pytest.fixture
def empty_cur():
    return create_curriculum("Test")


@pytest.fixture
def food_nouns():
    return [_NOUN(w) for w in ["water", "rice", "fish", "meat", "egg"]]


@pytest.fixture
def food_verbs():
    return [_VERB(w) for w in ["to eat", "to drink", "to cook"]]


# ─── Grammar Progression table integrity ─────────────────────────────────────

class TestGrammarProgressionTable:
    _REQUIRED = {"id", "structure", "pattern", "description", "example_jp",
                 "example_en", "tenses", "polarities", "requires", "level"}

    def test_all_required_fields_present(self):
        for g in GRAMMAR_PROGRESSION:
            missing = self._REQUIRED - g.keys()
            assert not missing, f"{g['id']!r} missing fields: {missing}"

    def test_ids_are_unique(self):
        ids = [g["id"] for g in GRAMMAR_PROGRESSION]
        assert len(ids) == len(set(ids)), "Duplicate grammar IDs found"

    def test_all_prerequisite_ids_exist(self):
        valid_ids = {g["id"] for g in GRAMMAR_PROGRESSION}
        for g in GRAMMAR_PROGRESSION:
            for req in g["requires"]:
                assert req in valid_ids, (
                    f"{g['id']!r} has unknown prerequisite {req!r}"
                )

    def test_no_self_referential_prerequisites(self):
        for g in GRAMMAR_PROGRESSION:
            assert g["id"] not in g["requires"], (
                f"{g['id']!r} lists itself as a prerequisite"
            )

    def test_level_1_steps_have_no_prerequisites(self):
        level1 = [g for g in GRAMMAR_PROGRESSION if g["level"] == 1]
        assert level1, "No level-1 grammar steps found"
        for g in level1:
            assert g["requires"] == [], (
                f"Level-1 step {g['id']!r} has prerequisites: {g['requires']}"
            )

    def test_at_least_one_step_per_level(self):
        levels = {g["level"] for g in GRAMMAR_PROGRESSION}
        for lvl in range(1, max(levels) + 1):
            assert any(g["level"] == lvl for g in GRAMMAR_PROGRESSION), (
                f"No grammar steps for level {lvl}"
            )

    def test_get_grammar_by_id_returns_correct_entry(self):
        g = get_grammar_by_id("action_present_affirmative")
        assert g["level"] == 1
        assert g["structure"] == "を-ます"

    def test_get_grammar_by_id_raises_on_unknown(self):
        with pytest.raises(KeyError):
            get_grammar_by_id("nonexistent_id")


# ─── get_next_grammar ─────────────────────────────────────────────────────────

class TestGetNextGrammar:
    def test_empty_covered_returns_only_level1(self):
        unlocked = get_next_grammar([])
        assert len(unlocked) >= 1
        for g in unlocked:
            assert g["requires"] == [], "Non-level-1 step returned when nothing covered"

    def test_level1_steps_are_sorted_first(self):
        unlocked = get_next_grammar([])
        levels = [g["level"] for g in unlocked]
        assert levels == sorted(levels)

    def test_completing_prerequisite_unlocks_dependent(self):
        """Covering action_present_affirmative must unlock action_present_negative."""
        before = {g["id"] for g in get_next_grammar([])}
        assert "action_present_negative" not in before

        after = {g["id"] for g in get_next_grammar(["action_present_affirmative"])}
        assert "action_present_negative" in after

    def test_step_not_returned_if_already_covered(self):
        covered = ["action_present_affirmative"]
        unlocked_ids = {g["id"] for g in get_next_grammar(covered)}
        assert "action_present_affirmative" not in unlocked_ids

    def test_multi_prerequisite_step_not_unlocked_until_all_covered(self):
        """action_past_negative requires both action_present_negative AND action_past_affirmative."""
        only_neg = ["action_present_affirmative", "action_present_negative"]
        ids_neg = {g["id"] for g in get_next_grammar(only_neg)}
        assert "action_past_negative" not in ids_neg

        both = only_neg + ["action_past_affirmative"]
        ids_both = {g["id"] for g in get_next_grammar(both)}
        assert "action_past_negative" in ids_both

    def test_all_covered_returns_empty(self):
        all_ids = [g["id"] for g in GRAMMAR_PROGRESSION]
        assert get_next_grammar(all_ids) == []


# ─── create_curriculum ────────────────────────────────────────────────────────

class TestCreateCurriculum:
    def test_has_required_keys(self):
        cur = create_curriculum()
        for key in ("name", "created_at", "lessons",
                    "covered_nouns", "covered_verbs", "covered_grammar_ids"):
            assert key in cur

    def test_initial_values_empty(self):
        cur = create_curriculum()
        assert cur["lessons"] == []
        assert cur["covered_nouns"] == []
        assert cur["covered_verbs"] == []
        assert cur["covered_grammar_ids"] == []

    def test_custom_name(self):
        cur = create_curriculum("My Course")
        assert cur["name"] == "My Course"


# ─── add_lesson ───────────────────────────────────────────────────────────────

class TestAddLesson:
    def test_adds_lesson_to_list(self, empty_cur, food_nouns, food_verbs):
        add_lesson(
            empty_cur,
            title="Lesson 1",
            theme="food",
            nouns=food_nouns[:2],
            verbs=food_verbs[:1],
            grammar_ids=["action_present_affirmative"],
        )
        assert len(empty_cur["lessons"]) == 1

    def test_lesson_has_correct_fields(self, empty_cur, food_nouns, food_verbs):
        lesson = add_lesson(
            empty_cur,
            title="Lesson 1",
            theme="food",
            nouns=food_nouns[:2],
            verbs=food_verbs[:1],
            grammar_ids=["action_present_affirmative"],
        )
        assert lesson["title"] == "Lesson 1"
        assert lesson["theme"] == "food"
        assert lesson["nouns"] == ["water", "rice"]
        assert lesson["verbs"] == ["to eat"]
        assert lesson["grammar_ids"] == ["action_present_affirmative"]
        assert lesson["status"] == "draft"

    def test_add_two_lessons_increments_id(self, empty_cur, food_nouns, food_verbs):
        l1 = add_lesson(empty_cur, title="L1", theme="food",
                        nouns=[], verbs=[], grammar_ids=[])
        l2 = add_lesson(empty_cur, title="L2", theme="food",
                        nouns=[], verbs=[], grammar_ids=[])
        assert l2["id"] == l1["id"] + 1

    def test_covered_trackers_not_updated_before_complete(self, empty_cur, food_nouns, food_verbs):
        add_lesson(
            empty_cur, title="L1", theme="food",
            nouns=food_nouns[:2], verbs=food_verbs[:1],
            grammar_ids=["action_present_affirmative"],
        )
        assert empty_cur["covered_nouns"] == []
        assert empty_cur["covered_grammar_ids"] == []


# ─── complete_lesson ──────────────────────────────────────────────────────────

class TestCompletedLesson:
    def _add_and_complete(self, cur, nouns, verbs, grammar_ids):
        lesson = add_lesson(
            cur, title="Lesson 1", theme="food",
            nouns=nouns, verbs=verbs, grammar_ids=grammar_ids,
        )
        complete_lesson(cur, lesson["id"])
        return lesson

    def test_status_set_to_completed(self, empty_cur, food_nouns, food_verbs):
        lesson = self._add_and_complete(
            empty_cur, food_nouns[:2], food_verbs[:1],
            ["action_present_affirmative"],
        )
        assert lesson["status"] == "completed"

    def test_covered_nouns_updated(self, empty_cur, food_nouns, food_verbs):
        self._add_and_complete(
            empty_cur, food_nouns[:2], food_verbs[:1],
            ["action_present_affirmative"],
        )
        assert "water" in empty_cur["covered_nouns"]
        assert "rice" in empty_cur["covered_nouns"]

    def test_covered_verbs_updated(self, empty_cur, food_nouns, food_verbs):
        self._add_and_complete(
            empty_cur, food_nouns[:2], food_verbs[:1],
            ["action_present_affirmative"],
        )
        assert "to eat" in empty_cur["covered_verbs"]

    def test_covered_grammar_updated(self, empty_cur, food_nouns, food_verbs):
        self._add_and_complete(
            empty_cur, [], [],
            ["action_present_affirmative", "identity_present_affirmative"],
        )
        assert "action_present_affirmative" in empty_cur["covered_grammar_ids"]
        assert "identity_present_affirmative" in empty_cur["covered_grammar_ids"]

    def test_raises_on_unknown_lesson_id(self, empty_cur):
        with pytest.raises(KeyError):
            complete_lesson(empty_cur, lesson_id=99)

    def test_no_duplicate_covered_nouns_after_two_lessons(self, empty_cur, food_nouns, food_verbs):
        for _ in range(2):
            lesson = add_lesson(
                empty_cur, title="L", theme="food",
                nouns=food_nouns[:2], verbs=[], grammar_ids=[],
            )
            complete_lesson(empty_cur, lesson["id"])
        assert len(empty_cur["covered_nouns"]) == len(set(empty_cur["covered_nouns"]))


# ─── suggest_new_vocab ────────────────────────────────────────────────────────

class TestSuggestNewVocab:
    def test_returns_fresh_items_first(self, food_nouns, food_verbs):
        nouns, verbs = suggest_new_vocab(
            food_nouns, food_verbs,
            covered_nouns=["water", "rice"],
            covered_verbs=[],
            num_nouns=3, num_verbs=2,
        )
        assert "water" not in [n["english"] for n in nouns]
        assert "rice" not in [n["english"] for n in nouns]

    def test_respects_num_nouns_and_verbs(self, food_nouns, food_verbs):
        nouns, verbs = suggest_new_vocab(
            food_nouns, food_verbs,
            covered_nouns=[], covered_verbs=[],
            num_nouns=3, num_verbs=2,
        )
        assert len(nouns) == 3
        assert len(verbs) == 2

    def test_fills_up_from_covered_when_fresh_exhausted(self, food_nouns, food_verbs):
        # Cover all nouns — should still return 3 (from already-covered pool)
        all_noun_names = [n["english"] for n in food_nouns]
        nouns, _ = suggest_new_vocab(
            food_nouns, food_verbs,
            covered_nouns=all_noun_names, covered_verbs=[],
            num_nouns=3, num_verbs=0,
        )
        assert len(nouns) == 3

    def test_empty_covered_returns_items_in_order(self, food_nouns, food_verbs):
        nouns, _ = suggest_new_vocab(
            food_nouns, food_verbs,
            covered_nouns=[], covered_verbs=[],
            num_nouns=2, num_verbs=0,
        )
        assert nouns[0]["english"] == food_nouns[0]["english"]
        assert nouns[1]["english"] == food_nouns[1]["english"]


# ─── summary ─────────────────────────────────────────────────────────────────

class TestSummary:
    def test_returns_non_empty_string(self, empty_cur):
        result = summary(empty_cur)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_contains_name(self, empty_cur):
        result = summary(create_curriculum("My Course"))
        assert "My Course" in result

    def test_contains_unlocked_grammar_header_for_fresh_curriculum(self, empty_cur):
        result = summary(empty_cur)
        assert "unlocked" in result.lower() or "available" in result.lower()

    def test_completed_curriculum_says_complete(self):
        all_ids = [g["id"] for g in GRAMMAR_PROGRESSION]
        cur = create_curriculum()
        cur["covered_grammar_ids"] = all_ids
        result = summary(cur)
        assert "complete" in result.lower()


# ─── load / save round-trip ───────────────────────────────────────────────────

class TestLoadSave:
    def test_round_trip(self, tmp_path, empty_cur, food_nouns, food_verbs):
        lesson = add_lesson(
            empty_cur, title="L1", theme="food",
            nouns=food_nouns[:2], verbs=food_verbs[:1],
            grammar_ids=["action_present_affirmative"],
        )
        complete_lesson(empty_cur, lesson["id"])

        path = tmp_path / "curriculum.json"
        save_curriculum(empty_cur, path)

        loaded = load_curriculum(path)
        assert loaded["name"] == empty_cur["name"]
        assert len(loaded["lessons"]) == 1
        assert loaded["covered_nouns"] == empty_cur["covered_nouns"]
        assert loaded["covered_grammar_ids"] == empty_cur["covered_grammar_ids"]

    def test_load_nonexistent_returns_fresh_curriculum(self, tmp_path):
        path = tmp_path / "does_not_exist.json"
        cur = load_curriculum(path)
        assert cur["lessons"] == []
        assert cur["covered_nouns"] == []

    def test_save_creates_parent_directories(self, tmp_path):
        path = tmp_path / "subdir" / "nested" / "curriculum.json"
        save_curriculum(create_curriculum(), path)
        assert path.exists()

    def test_saved_file_is_valid_json_with_unicode(self, tmp_path, food_nouns, food_verbs):
        cur = create_curriculum("テスト")
        path = tmp_path / "cur.json"
        save_curriculum(cur, path)
        raw = path.read_text(encoding="utf-8")
        parsed = json.loads(raw)
        assert parsed["name"] == "テスト"
