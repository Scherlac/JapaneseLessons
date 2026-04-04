"""
Lesson content persistence.

Writes and reads per-lesson content.json files under the lesson bundle dir.
The curriculum.json remains the index; content files are the payload.
"""

from __future__ import annotations

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
