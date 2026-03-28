"""
Language-agnostic curriculum CRUD, vocab selection, and grammar progression helpers.

All functions operate on plain curriculum dicts and are independent of any
specific language pair's grammar progression table.
"""

from __future__ import annotations

import json
import random
from datetime import datetime, timezone
from pathlib import Path

from ..models import GrammarItem


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


# ── Grammar Helpers ───────────────────────────────────────────────────────────

def get_next_grammar_from(
    progression: list[GrammarItem],
    covered_grammar_ids: list[str],
) -> list[GrammarItem]:
    """Return unlocked grammar steps from *progression* not in *covered*.

    A step is unlocked when all its prerequisites appear in covered_grammar_ids.
    Results are sorted by level (easiest first).
    """
    covered = set(covered_grammar_ids)
    return sorted(
        [
            g for g in progression
            if g.id not in covered
            and all(req in covered for req in g.requires)
        ],
        key=lambda g: g.level,
    )


def grammar_summary_lines(grammar_entries: list[dict]) -> list[str]:
    """Format a list of grammar entries as short human-readable lines."""
    return [
        f"  [{g['level']}] {g['id']}: {g['pattern']} — {g['description']}"
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


# ── Internal helpers ──────────────────────────────────────────────────────────

def _now() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )
