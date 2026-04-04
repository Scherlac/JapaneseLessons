"""
Language-agnostic curriculum CRUD and grammar progression helpers.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field

from ..models import GrammarItem


# ── Internal helpers ──────────────────────────────────────────────────────────

def _now() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


# ── Typed curriculum models ───────────────────────────────────────────────────

class LessonRecord(BaseModel):
    """A single lesson entry persisted in curriculum.json."""

    id: int
    title: str
    theme: str
    nouns: dict[str, str]
    verbs: dict[str, str]
    adjectives: dict[str, str]
    grammar_ids: list[str]
    items_count: int = 0
    status: str = "draft"
    created_at: str = Field(default_factory=_now)
    completed_at: str | None = None


class CurriculumData(BaseModel):
    """Typed in-memory curriculum state loaded from / persisted to curriculum.json."""

    name: str = Field(default="My well-structured curriculum", description="A human-friendly name for this curriculum")
    level_details: str = Field(default="beginner-level", description="Details about the target lesson level, for use in prompts")
    created_at: str = Field(default_factory=_now)
    lessons: list[LessonRecord] = Field(default_factory=list)
    covered_nouns: list[str] = Field(default_factory=list)
    covered_verbs: list[str] = Field(default_factory=list)
    covered_grammar_ids: list[str] = Field(default_factory=list)


# ── Curriculum CRUD ───────────────────────────────────────────────────────────

def create_curriculum(name: str = "My well-structured curriculum", level_details: str = "beginner-level") -> CurriculumData:
    """Return a fresh empty CurriculumData."""
    return CurriculumData(name=name, level_details=level_details)


def load_curriculum(path: Path) -> CurriculumData:
    """Load curriculum from a JSON file.

    Returns a fresh empty CurriculumData if the file does not exist yet.
    """
    path = Path(path)
    if not path.exists():
        return create_curriculum()
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return CurriculumData.model_validate(data)


def save_curriculum(curriculum: CurriculumData, path: Path) -> None:
    """Save CurriculumData to a JSON file (creates parent directories as needed)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        curriculum.model_dump_json(indent=2),
        encoding="utf-8",
    )


# ── Lesson Management ─────────────────────────────────────────────────────────

def add_lesson(
    curriculum: CurriculumData,
    *,
    title: str,
    theme: str,
    nouns: dict[str, str],
    verbs: dict[str, str],
    adjectives: dict[str, str],
    grammar_ids: list[str],
    items_count: int = 0,
    status: str = "draft",
) -> LessonRecord:
    """Add a new lesson entry to the curriculum and return the LessonRecord.

    Does NOT update covered_* trackers — call complete_lesson() to do that.
    """
    next_id = max((ln.id for ln in curriculum.lessons), default=0) + 1
    lesson = LessonRecord(
        id=next_id,
        title=title,
        theme=theme,
        nouns=nouns
        verbs=verbs,
        adjectives=adjectives,
        grammar_ids=grammar_ids,
        items_count=items_count,
        status=status,
        created_at=_now(),
    )
    curriculum.lessons.append(lesson)
    return lesson


def replace_lesson(
    curriculum: CurriculumData,
    *,
    lesson_id: int,
    title: str,
    theme: str,
    nouns: dict[str, str],
    verbs: dict[str, str],
    adjectives: dict[str, str],
    grammar_ids: list[str],
    items_count: int = 0,
    status: str = "draft",
) -> LessonRecord:
    """Replace an existing lesson entry and return the updated LessonRecord."""
    lesson = _get_lesson(curriculum, lesson_id)
    lesson.title = title
    lesson.theme = theme
    lesson.nouns = nouns
    lesson.verbs = verbs
    lesson.adjectives = adjectives
    lesson.grammar_ids = grammar_ids
    lesson.items_count = items_count
    lesson.status = status
    lesson.created_at = _now()
    lesson.completed_at = None
    return lesson


def recompute_coverage(curriculum: CurriculumData) -> None:
    """Rebuild covered vocab/grammar trackers from completed lessons."""
    covered_nouns: set[str] = set()
    covered_verbs: set[str] = set()
    covered_adjectives: set[str] = set()
    covered_grammar: set[str] = set()

    for lesson in curriculum.lessons:
        if lesson.status != "completed":
            continue
        covered_nouns.update(lesson.nouns)
        covered_verbs.update(lesson.verbs)
        covered_adjectives.update(lesson.adjectives)
        covered_grammar.update(lesson.grammar_ids)

    curriculum.covered_nouns = sorted(covered_nouns)
    curriculum.covered_verbs = sorted(covered_verbs)
    curriculum.covered_adjectives = sorted(covered_adjectives)
    curriculum.covered_grammar_ids = sorted(covered_grammar)


def complete_lesson(curriculum: CurriculumData, lesson_id: int) -> None:
    """Mark a lesson as completed and update covered vocab/grammar trackers."""
    lesson = _get_lesson(curriculum, lesson_id)
    lesson.status = "completed"
    lesson.completed_at = _now()
    recompute_coverage(curriculum)


def _get_lesson(curriculum: CurriculumData, lesson_id: int) -> LessonRecord:
    for lesson in curriculum.lessons:
        if lesson.id == lesson_id:
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


def grammar_summary_lines(grammar_entries: list[GrammarItem]) -> list[str]:
    """Format a list of GrammarItem objects as short human-readable lines."""
    return [
        f"  [{g.level}] {g.id}: {g.pattern} \u2014 {g.description}"
        for g in grammar_entries
    ]



