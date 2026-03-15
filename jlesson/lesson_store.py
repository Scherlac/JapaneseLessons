"""
Lesson content persistence.

Writes and reads per-lesson content.json files under output/<lesson_id>/content.json.
The curriculum.json remains the index; content files are the payload.
"""

from __future__ import annotations

from pathlib import Path

from .models import LessonContent

_DEFAULT_OUTPUT_DIR = Path(__file__).parent.parent / "output"


def save_lesson_content(
    content: LessonContent,
    output_dir: Path | None = None,
) -> Path:
    """Persist lesson content to output/<lesson_id>/content.json.

    Creates the directory if it does not exist.
    Returns the path of the written file.
    """
    base = Path(output_dir) if output_dir is not None else _DEFAULT_OUTPUT_DIR
    lesson_dir = base / f"lesson_{content.lesson_id:03d}"
    lesson_dir.mkdir(parents=True, exist_ok=True)
    path = lesson_dir / "content.json"
    path.write_text(
        content.model_dump_json(indent=2, exclude_none=True),
        encoding="utf-8",
    )
    return path


def load_lesson_content(
    lesson_id: int,
    output_dir: Path | None = None,
) -> LessonContent:
    """Load lesson content from output/<lesson_id>/content.json.

    Raises FileNotFoundError if the file does not exist.
    """
    base = Path(output_dir) if output_dir is not None else _DEFAULT_OUTPUT_DIR
    path = base / f"lesson_{lesson_id:03d}" / "content.json"
    if not path.exists():
        raise FileNotFoundError(
            f"No content found for lesson {lesson_id} at {path}"
        )
    return LessonContent.model_validate_json(path.read_text(encoding="utf-8"))
