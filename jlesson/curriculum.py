"""
Curriculum module — lesson dictionary and grammar progression tracker.

Tracks which vocabulary and grammar has been covered lesson-by-lesson
and provides tools to select the next grammar points and vocab subset.

The grammar progression table defines an ordered, prerequisite-aware
sequence of grammar structures from beginner through intermediate level.

Usage:
    from curriculum import create_curriculum, load_curriculum, save_curriculum
    from curriculum import get_next_grammar, add_lesson, complete_lesson, summary

    cur = create_curriculum("Japanese Beginner")
    unlocked = get_next_grammar(cur["covered_grammar_ids"])
    for g in unlocked:
        print(g["id"], "—", g["description"])
"""

from __future__ import annotations

import json
import random
from datetime import datetime, timezone
from pathlib import Path

# ── Grammar Progression Tables ────────────────────────────────────────────────
# Each entry defines one grammar dimension with its prerequisites.
# Items are ordered: easiest first, prerequisites always listed before dependents.
#
# Naming convention — direction-based:
#   ENG_TO_JAP  = English speaker learning Japanese
#   HUN_TO_ENG  = Hungarian speaker learning English

# ── English → Japanese (existing, levels 1-4) ────────────────────────────────
# "level" is a rough JLPT-aligned difficulty bucket (1 = absolute beginner).

ENG_TO_JAP_GRAMMAR_PROGRESSION: list[dict] = [
    # ── Level 1 — absolute beginner, no prerequisites ────────────────────────
    {
        "id": "action_present_affirmative",
        "structure": "を-ます",
        "pattern": "Action",
        "description": "Subject does verb to object — present affirmative (polite)",
        "example_jp": "私は魚を食べます。",
        "example_en": "I eat fish.",
        "tenses": ["present"],
        "polarities": ["affirmative"],
        "requires": [],
        "level": 1,
    },
    {
        "id": "identity_present_affirmative",
        "structure": "は-です",
        "pattern": "Identity",
        "description": "A is B — identity / description sentence",
        "example_jp": "これはパンです。",
        "example_en": "This is bread.",
        "tenses": ["present"],
        "polarities": ["affirmative"],
        "requires": [],
        "level": 1,
    },
    # ── Level 2 — requires one level-1 milestone ─────────────────────────────
    {
        "id": "action_present_negative",
        "structure": "を-ません",
        "pattern": "Action",
        "description": "Subject does NOT verb object — present negative (polite)",
        "example_jp": "彼は肉を食べません。",
        "example_en": "He does not eat meat.",
        "tenses": ["present"],
        "polarities": ["negative"],
        "requires": ["action_present_affirmative"],
        "level": 2,
    },
    {
        "id": "action_past_affirmative",
        "structure": "を-ました",
        "pattern": "Action",
        "description": "Subject did verb to object — past affirmative (polite)",
        "example_jp": "私は水を飲みました。",
        "example_en": "I drank water.",
        "tenses": ["past"],
        "polarities": ["affirmative"],
        "requires": ["action_present_affirmative"],
        "level": 2,
    },
    {
        "id": "question_ka",
        "structure": "〜か",
        "pattern": "Question",
        "description": "Yes/no question — append か to any polite sentence",
        "example_jp": "あなたはお茶を飲みますか。",
        "example_en": "Do you drink tea?",
        "tenses": ["present"],
        "polarities": ["affirmative"],
        "requires": ["action_present_affirmative"],
        "level": 2,
    },
    {
        "id": "direction_ni_ikimasu",
        "structure": "に/へ-行きます",
        "pattern": "Direction",
        "description": "Subject goes to destination — destination particle に/へ",
        "example_jp": "私は駅に行きます。",
        "example_en": "I go to the station.",
        "tenses": ["present"],
        "polarities": ["affirmative"],
        "requires": ["action_present_affirmative"],
        "level": 2,
    },
    {
        "id": "existence_arimasu",
        "structure": "に-あります",
        "pattern": "Existence",
        "description": "There is X at/in Y — inanimate objects (あります)",
        "example_jp": "テーブルにパンがあります。",
        "example_en": "There is bread on the table.",
        "tenses": ["present"],
        "polarities": ["affirmative"],
        "requires": ["action_present_affirmative"],
        "level": 2,
    },
    {
        "id": "adjective_na",
        "structure": "は-な-adj-です",
        "pattern": "Adjective",
        "description": "な-adjective predicate — subject is [な-adjective]",
        "example_jp": "この料理は好きです。",
        "example_en": "I like this dish. (lit: This dish is liked.)",
        "tenses": ["present"],
        "polarities": ["affirmative"],
        "requires": ["identity_present_affirmative"],
        "level": 2,
    },
    # ── Level 3 — requires two level-2 milestones ────────────────────────────
    {
        "id": "action_past_negative",
        "structure": "を-ませんでした",
        "pattern": "Action",
        "description": "Subject did NOT verb object — past negative (polite)",
        "example_jp": "私は昨日野菜を食べませんでした。",
        "example_en": "I did not eat vegetables yesterday.",
        "tenses": ["past"],
        "polarities": ["negative"],
        "requires": ["action_present_negative", "action_past_affirmative"],
        "level": 3,
    },
    {
        "id": "desire_tai",
        "structure": "V-たいです",
        "pattern": "Desire",
        "description": "Subject wants to do verb — verb stem + たいです",
        "example_jp": "私はお茶を飲みたいです。",
        "example_en": "I want to drink tea.",
        "tenses": ["present"],
        "polarities": ["affirmative"],
        "requires": ["action_present_affirmative", "action_present_negative"],
        "level": 3,
    },
    {
        "id": "desire_hoshii",
        "structure": "が-ほしいです",
        "pattern": "Desire",
        "description": "Subject wants noun — subject が ほしいです",
        "example_jp": "私は水がほしいです。",
        "example_en": "I want water.",
        "tenses": ["present"],
        "polarities": ["affirmative"],
        "requires": ["action_present_affirmative"],
        "level": 3,
    },
    {
        "id": "reason_kara",
        "structure": "〜から",
        "pattern": "Reason",
        "description": "Because … — append から to a clause to give a reason",
        "example_jp": "お腹が空いていますから、ご飯を食べます。",
        "example_en": "Because I am hungry, I eat rice.",
        "tenses": ["present"],
        "polarities": ["affirmative"],
        "requires": ["action_present_affirmative", "action_present_negative"],
        "level": 3,
    },
    # ── Level 4 — intermediate────────────────────────────────────────────────
    {
        "id": "te_form_request",
        "structure": "V-てください",
        "pattern": "Request",
        "description": "Please do verb — て-form + ください",
        "example_jp": "パンを食べてください。",
        "example_en": "Please eat the bread.",
        "tenses": ["present"],
        "polarities": ["affirmative"],
        "requires": ["action_present_affirmative", "desire_tai"],
        "level": 4,
    },
    {
        "id": "te_form_progressive",
        "structure": "V-ています",
        "pattern": "Progressive",
        "description": "Subject is doing verb — て-form + います (continuous aspect)",
        "example_jp": "彼は今ご飯を食べています。",
        "example_en": "He is eating rice now.",
        "tenses": ["present"],
        "polarities": ["affirmative"],
        "requires": ["te_form_request"],
        "level": 4,
    },
    {
        "id": "potential_dekimasu",
        "structure": "V-られます/できます",
        "pattern": "Potential",
        "description": "Subject can do verb — potential form / できます",
        "example_jp": "私は日本語が話せます。",
        "example_en": "I can speak Japanese.",
        "tenses": ["present"],
        "polarities": ["affirmative"],
        "requires": ["action_present_affirmative", "action_present_negative"],
        "level": 4,
    },
]

# Backward-compat alias — existing code imports GRAMMAR_PROGRESSION everywhere.
GRAMMAR_PROGRESSION = ENG_TO_JAP_GRAMMAR_PROGRESSION


# ── Hungarian → English (levels 1-6) ─────────────────────────────────────────
# English grammar progression for Hungarian-speaking children (ages 8-12).
# 26 grammar points across 6 prerequisite-aware levels.
# No Japanese-specific fields (structure, tenses, polarities are not used).

HUN_TO_ENG_GRAMMAR_PROGRESSION: list[dict] = [
    # ── Level 1 — absolute beginner, no prerequisites ────────────────────────
    {
        "id": "present_simple_affirmative",
        "pattern": "Subject + verb + object",
        "description": "Simple present tense — affirmative",
        "example_en": "I eat bread.",
        "example_hu": "Én kenyeret eszem.",
        "requires": [],
        "level": 1,
    },
    {
        "id": "identity_is_am_are",
        "pattern": "Subject + is/am/are + noun/adjective",
        "description": "Identity / description with be-verb",
        "example_en": "She is a teacher.",
        "example_hu": "Ő tanárnő.",
        "requires": [],
        "level": 1,
    },
    # ── Level 2 — requires Level 1 ───────────────────────────────────────────
    {
        "id": "present_simple_negative",
        "pattern": "Subject + do/does not + verb",
        "description": "Simple present tense — negative",
        "example_en": "I do not eat fish.",
        "example_hu": "Én nem eszem halat.",
        "requires": ["present_simple_affirmative"],
        "level": 2,
    },
    {
        "id": "present_simple_question",
        "pattern": "Do/Does + subject + verb?",
        "description": "Simple present tense — yes/no question",
        "example_en": "Do you like cats?",
        "example_hu": "Szereted a macskákat?",
        "requires": ["present_simple_affirmative"],
        "level": 2,
    },
    {
        "id": "can_ability",
        "pattern": "Subject + can + verb",
        "description": "Ability with can",
        "example_en": "I can swim fast.",
        "example_hu": "Tudok gyorsan úszni.",
        "requires": ["present_simple_affirmative"],
        "level": 2,
    },
    {
        "id": "have_got",
        "pattern": "Subject + have/has got + noun",
        "description": "Possession with have got",
        "example_en": "I have got a dog.",
        "example_hu": "Van egy kutyám.",
        "requires": ["present_simple_affirmative"],
        "level": 2,
    },
    # ── Level 3 — requires Level 2 ───────────────────────────────────────────
    {
        "id": "present_continuous",
        "pattern": "Subject + is/am/are + verb-ing",
        "description": "Present continuous — action happening now",
        "example_en": "I am eating now.",
        "example_hu": "Most eszem.",
        "requires": ["present_simple_affirmative", "identity_is_am_are"],
        "level": 3,
    },
    {
        "id": "present_continuous_question",
        "pattern": "Is/Am/Are + subject + verb-ing?",
        "description": "Present continuous — yes/no question",
        "example_en": "Are you eating now?",
        "example_hu": "Most eszel?",
        "requires": ["present_continuous", "present_simple_question"],
        "level": 3,
    },
    {
        "id": "present_continuous_negative",
        "pattern": "Subject + is/am/are not + verb-ing",
        "description": "Present continuous — negative",
        "example_en": "She is not eating right now.",
        "example_hu": "Ő most nem eszik.",
        "requires": ["present_continuous", "present_simple_negative"],
        "level": 3,
    },
    {
        "id": "there_is_are",
        "pattern": "There is/are + noun",
        "description": "Existence — there is / there are",
        "example_en": "There is a cat on the table.",
        "example_hu": "Van egy macska az asztalon.",
        "requires": ["identity_is_am_are"],
        "level": 3,
    },
    # ── Level 4 — requires Level 3 ───────────────────────────────────────────
    {
        "id": "past_simple_affirmative",
        "pattern": "Subject + past verb + object",
        "description": "Simple past tense — affirmative",
        "example_en": "I ate bread yesterday.",
        "example_hu": "Tegnap kenyeret ettem.",
        "requires": ["present_simple_affirmative"],
        "level": 4,
    },
    {
        "id": "past_simple_negative",
        "pattern": "Subject + did not + verb",
        "description": "Simple past tense — negative",
        "example_en": "I did not eat fish.",
        "example_hu": "Nem ettem halat.",
        "requires": ["past_simple_affirmative", "present_simple_negative"],
        "level": 4,
    },
    {
        "id": "past_simple_question",
        "pattern": "Did + subject + verb?",
        "description": "Simple past tense — yes/no question",
        "example_en": "Did you run today?",
        "example_hu": "Futottál ma?",
        "requires": ["past_simple_affirmative", "present_simple_question"],
        "level": 4,
    },
    {
        "id": "be_was_were",
        "pattern": "Subject + was/were + noun/adjective",
        "description": "Past tense of be — was / were",
        "example_en": "They were happy last week.",
        "example_hu": "Boldogok voltak a múlt héten.",
        "requires": ["identity_is_am_are", "past_simple_affirmative"],
        "level": 4,
    },
    {
        "id": "regular_verbs_formation",
        "pattern": "Base verb + -ed",
        "description": "Regular past tense formation — add -ed",
        "example_en": "walk → walked, play → played",
        "example_hu": "sétál → sétált, játszik → játszott",
        "requires": ["past_simple_affirmative"],
        "level": 4,
    },
    {
        "id": "irregular_verbs_3forms_1",
        "pattern": "base / past / past participle",
        "description": "Common irregular verbs — three forms (set 1)",
        "example_en": "go/went/gone, eat/ate/eaten",
        "example_hu": "megy/ment, eszik/evett",
        "requires": ["past_simple_affirmative"],
        "level": 4,
    },
    # ── Level 5 — requires Level 4 ───────────────────────────────────────────
    {
        "id": "past_continuous",
        "pattern": "Subject + was/were + verb-ing",
        "description": "Past continuous — action was happening",
        "example_en": "I was eating when you called.",
        "example_hu": "Éppen ettem, amikor hívtál.",
        "requires": ["present_continuous", "past_simple_affirmative"],
        "level": 5,
    },
    {
        "id": "past_continuous_question",
        "pattern": "Was/Were + subject + verb-ing?",
        "description": "Past continuous — yes/no question",
        "example_en": "Were you eating when I called?",
        "example_hu": "Ettél, amikor hívtalak?",
        "requires": ["past_continuous", "past_simple_question"],
        "level": 5,
    },
    {
        "id": "past_continuous_negative",
        "pattern": "Subject + was/were not + verb-ing",
        "description": "Past continuous — negative",
        "example_en": "She was not eating when I arrived.",
        "example_hu": "Nem evett, amikor megérkeztem.",
        "requires": ["past_continuous", "past_simple_negative"],
        "level": 5,
    },
    {
        "id": "irregular_verbs_3forms_2",
        "pattern": "base / past / past participle",
        "description": "More irregular verbs — three forms (set 2)",
        "example_en": "see/saw/seen, take/took/taken",
        "example_hu": "lát/látott, vesz/vett",
        "requires": ["irregular_verbs_3forms_1"],
        "level": 5,
    },
    {
        "id": "will_future",
        "pattern": "Subject + will + verb",
        "description": "Simple future with will",
        "example_en": "I will eat later.",
        "example_hu": "Később fogok enni.",
        "requires": ["present_simple_affirmative"],
        "level": 5,
    },
    {
        "id": "going_to_future",
        "pattern": "Subject + is/am/are going to + verb",
        "description": "Near future with going to",
        "example_en": "I am going to eat lunch.",
        "example_hu": "Ebédelni fogok.",
        "requires": ["present_continuous"],
        "level": 5,
    },
    # ── Level 6 — requires Level 5 ───────────────────────────────────────────
    {
        "id": "comparisons",
        "pattern": "noun + is + adjective-er + than + noun",
        "description": "Comparatives — comparing two things",
        "example_en": "The dog is bigger than the cat.",
        "example_hu": "A kutya nagyobb, mint a macska.",
        "requires": ["identity_is_am_are"],
        "level": 6,
    },
    {
        "id": "present_perfect",
        "pattern": "Subject + has/have + past participle",
        "description": "Present perfect — completed action with current relevance",
        "example_en": "I have eaten already.",
        "example_hu": "Már ettem.",
        "requires": ["past_simple_affirmative", "irregular_verbs_3forms_1"],
        "level": 6,
    },
    {
        "id": "first_conditional",
        "pattern": "If + present, subject + will + verb",
        "description": "First conditional — real possibility",
        "example_en": "If it rains, I will stay home.",
        "example_hu": "Ha esik az eső, otthon maradok.",
        "requires": ["will_future", "present_simple_affirmative"],
        "level": 6,
    },
    {
        "id": "must_should",
        "pattern": "Subject + must/should + verb",
        "description": "Obligation and advice — must / should",
        "example_en": "You must study every day.",
        "example_hu": "Minden nap tanulnod kell.",
        "requires": ["present_simple_affirmative", "can_ability"],
        "level": 6,
    },
]


# Fast lookup by id — Japanese
_GRAMMAR_BY_ID: dict[str, dict] = {g["id"]: g for g in GRAMMAR_PROGRESSION}


# ── Curriculum CRUD ───────────────────────────────────────────────────────────

def create_curriculum(name: str = "Japanese Beginner") -> dict:
    """Return a fresh empty curriculum dict."""
    return {
        "name": name,
        "created_at": _now(),
        "lessons": [],
        "covered_nouns": [],
        "covered_verbs": [],
        "covered_grammar_ids": [],
    }


def load_curriculum(path: Path) -> dict:
    """Load curriculum from a JSON file.

    Returns a fresh empty curriculum if the file does not exist yet.
    """
    path = Path(path)
    if not path.exists():
        return create_curriculum()
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_curriculum(curriculum: dict, path: Path) -> None:
    """Save curriculum to a JSON file (creates parent directories as needed)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(curriculum, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# ── Lesson Management ─────────────────────────────────────────────────────────

def add_lesson(
    curriculum: dict,
    *,
    title: str,
    theme: str,
    nouns: list[dict],
    verbs: list[dict],
    grammar_ids: list[str],
    items_count: int = 0,
    status: str = "draft",
) -> dict:
    """Add a new lesson entry to the curriculum and return the lesson dict.

    Does NOT update covered_* trackers — call complete_lesson() to do that.
    """
    next_id = max((ln["id"] for ln in curriculum["lessons"]), default=0) + 1
    lesson = {
        "id": next_id,
        "title": title,
        "theme": theme,
        "nouns": [n["english"] for n in nouns],
        "verbs": [v["english"] for v in verbs],
        "grammar_ids": list(grammar_ids),
        "items_count": items_count,
        "status": status,
        "created_at": _now(),
    }
    curriculum["lessons"].append(lesson)
    return lesson


def complete_lesson(curriculum: dict, lesson_id: int) -> None:
    """Mark a lesson as completed and update covered vocab/grammar trackers."""
    lesson = _get_lesson(curriculum, lesson_id)
    lesson["status"] = "completed"
    lesson["completed_at"] = _now()

    covered_nouns = set(curriculum["covered_nouns"])
    covered_verbs = set(curriculum["covered_verbs"])
    covered_grammar = set(curriculum["covered_grammar_ids"])

    covered_nouns.update(lesson["nouns"])
    covered_verbs.update(lesson["verbs"])
    covered_grammar.update(lesson["grammar_ids"])

    curriculum["covered_nouns"] = sorted(covered_nouns)
    curriculum["covered_verbs"] = sorted(covered_verbs)
    curriculum["covered_grammar_ids"] = sorted(covered_grammar)


def _get_lesson(curriculum: dict, lesson_id: int) -> dict:
    for lesson in curriculum["lessons"]:
        if lesson["id"] == lesson_id:
            return lesson
    raise KeyError(f"Lesson {lesson_id} not found in curriculum")


# ── Grammar Progression ───────────────────────────────────────────────────────

def get_next_grammar(covered_grammar_ids: list[str]) -> list[dict]:
    """Return grammar steps that are unlocked but not yet covered.

    A step is unlocked when all its prerequisites appear in covered_grammar_ids.
    Results are sorted by level (easiest first).
    """
    covered = set(covered_grammar_ids)
    return sorted(
        [
            g for g in GRAMMAR_PROGRESSION
            if g["id"] not in covered
            and all(req in covered for req in g["requires"])
        ],
        key=lambda g: g["level"],
    )


def get_grammar_by_id(grammar_id: str) -> dict:
    """Return a grammar spec by its id.  Raises KeyError if not found."""
    if grammar_id not in _GRAMMAR_BY_ID:
        raise KeyError(f"Unknown grammar id: {grammar_id!r}")
    return _GRAMMAR_BY_ID[grammar_id]


def grammar_summary_lines(grammar_entries: list[dict]) -> list[str]:
    """Format a list of grammar entries as short human-readable lines."""
    return [
        f"  [{g['level']}] {g['id']}: {g['structure']} — {g['description']}"
        for g in grammar_entries
    ]


# ── Vocab Selection ───────────────────────────────────────────────────────────

def suggest_new_vocab(
    all_nouns: list[dict],
    all_verbs: list[dict],
    covered_nouns: list[str],
    covered_verbs: list[str],
    num_nouns: int = 4,
    num_verbs: int = 3,
    *,
    seed: int | None = None,
) -> tuple[list[dict], list[dict]]:
    """Select vocab items not yet covered in previous lessons.

    Prioritises fresh items; fills up from already-covered items if the
    available pool is exhausted.

    Pass ``seed`` for a deterministic shuffled selection; omit (or ``None``)
    to get items in their original list order (backward-compatible).

    Returns:
        (selected_nouns, selected_verbs) — both lists of vocab dicts.
    """
    covered_n = set(covered_nouns)
    covered_v = set(covered_verbs)

    fresh_nouns = [n for n in all_nouns if n["english"] not in covered_n]
    fresh_verbs = [v for v in all_verbs if v["english"] not in covered_v]

    if seed is not None:
        rng = random.Random(seed)
        rng.shuffle(fresh_nouns)
        rng.shuffle(fresh_verbs)

    selected_nouns = fresh_nouns[:num_nouns]
    if len(selected_nouns) < num_nouns:
        seen = {n["english"] for n in selected_nouns}
        gap = num_nouns - len(selected_nouns)
        selected_nouns += [n for n in all_nouns if n["english"] not in seen][:gap]

    selected_verbs = fresh_verbs[:num_verbs]
    if len(selected_verbs) < num_verbs:
        seen = {v["english"] for v in selected_verbs}
        gap = num_verbs - len(selected_verbs)
        selected_verbs += [v for v in all_verbs if v["english"] not in seen][:gap]

    return selected_nouns[:num_nouns], selected_verbs[:num_verbs]


# ── Summary / Display ─────────────────────────────────────────────────────────

def summary(curriculum: dict) -> str:
    """Return a human-readable curriculum summary string."""
    lines = [
        f"Curriculum: {curriculum['name']}",
        f"  Total lessons : {len(curriculum['lessons'])}",
        f"  Covered nouns : {len(curriculum['covered_nouns'])}",
        f"  Covered verbs : {len(curriculum['covered_verbs'])}",
        f"  Grammar done  : {len(curriculum['covered_grammar_ids'])}",
    ]

    if curriculum["lessons"]:
        lines.append("")
        lines.append("  Lessons:")
        for lesson in curriculum["lessons"]:
            icon = "✅" if lesson["status"] == "completed" else "📝"
            grammar_str = ", ".join(lesson["grammar_ids"]) or "—"
            lines.append(
                f"    {icon} #{lesson['id']:02d}  {lesson['title']}"
                f"  ({lesson['items_count']} items | grammar: {grammar_str})"
            )

    unlocked = get_next_grammar(curriculum["covered_grammar_ids"])
    if unlocked:
        lines.append("")
        lines.append(f"  Next available grammar ({len(unlocked)} steps unlocked):")
        for g in unlocked[:5]:
            lines.append(f"    • [{g['level']}] {g['id']}: {g['description']}")
        if len(unlocked) > 5:
            lines.append(f"    … and {len(unlocked) - 5} more")
    else:
        lines.append("")
        lines.append("  All grammar steps have been covered — curriculum complete!")

    return "\n".join(lines)


# ── Internal helpers ──────────────────────────────────────────────────────────

def _now() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )
