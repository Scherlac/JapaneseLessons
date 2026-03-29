"""
Lesson content persistence.

Writes and reads per-lesson content.json files under the lesson bundle dir.
Also writes shared vocab JSON files at the language level.
The curriculum.json remains the index; content files are the payload.
"""

from __future__ import annotations

import json
from pathlib import Path

from .models import LessonContent


def save_lesson_content(
    content: LessonContent,
    lesson_dir: Path,
) -> Path:
    """Persist lesson content to ``lesson_dir/content.json``.

    Creates the directory if it does not exist.
    Returns the path of the written file.
    """
    lesson_dir = Path(lesson_dir)
    lesson_dir.mkdir(parents=True, exist_ok=True)
    path = lesson_dir / "content.json"
    path.write_text(
        content.model_dump_json(indent=2, exclude_none=True),
        encoding="utf-8",
    )
    return path


def load_lesson_content(
    lesson_id: int,
    lesson_dir: Path,
) -> LessonContent:
    """Load lesson content from ``lesson_dir/content.json``.

    Raises FileNotFoundError if the file does not exist.
    """
    path = Path(lesson_dir) / "content.json"
    if not path.exists():
        raise FileNotFoundError(
            f"No content found for lesson {lesson_id} at {path}"
        )
    return LessonContent.model_validate_json(path.read_text(encoding="utf-8"))


def save_shared_vocab(
    vocab_dir: Path,
    theme: str,
    nouns: list[dict],
    verbs: list[dict],
) -> Path:
    """Write (or update) the shared vocab file at ``vocab_dir/{theme}.json``.

    This file accumulates all vocabulary seen for a language+theme combination
    across all lesson runs, making it available for reuse and review.

    Returns the path of the written file.
    """
    vocab_dir = Path(vocab_dir)
    vocab_dir.mkdir(parents=True, exist_ok=True)
    path = vocab_dir / f"{theme}.json"

    existing: dict = {}
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            existing = {}

    seen_nouns = {n.get("id", "") for n in existing.get("nouns", []) if n.get("id")}
    seen_verbs = {v.get("id", "") for v in existing.get("verbs", []) if v.get("id")}

    merged_nouns = list(existing.get("nouns", []))
    merged_verbs = list(existing.get("verbs", []))
    merged_nouns.extend(n for n in nouns if n.get("id") not in seen_nouns)
    merged_verbs.extend(v for v in verbs if v.get("id") not in seen_verbs)

    payload = {"theme": theme, "nouns": merged_nouns, "verbs": merged_verbs}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
