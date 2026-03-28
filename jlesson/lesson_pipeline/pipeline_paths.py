from __future__ import annotations

from pathlib import Path

_DEFAULT_OUTPUT_BASE = Path(__file__).parent.parent / "output"


def _output_base(config) -> Path:
    return (
        Path(config.output_dir)
        if config.output_dir is not None
        else _DEFAULT_OUTPUT_BASE
    )


def resolve_lang_dir(config) -> Path:
    """Return ``{base}/{language}`` -- always includes the language code."""
    return _output_base(config) / config.language


def resolve_lesson_dir(config, lesson_id: int) -> Path:
    """Return the self-contained lesson bundle dir:
    ``{base}/{language}/{theme}/lesson_{id:03d}/``
    """
    return resolve_lang_dir(config) / config.theme / f"lesson_{lesson_id:03d}"


def resolve_vocab_dir(config) -> Path:
    """Return the shared vocab dir for the language:
    ``{base}/{language}/vocab/``
    """
    return resolve_lang_dir(config) / "vocab"


def resolve_output_dir(config) -> Path:
    """Return the language-level output dir ``{base}/{language}/``.

    Deprecated: prefer resolve_lesson_dir() for fully qualified lesson paths.
    """
    return resolve_lang_dir(config)
