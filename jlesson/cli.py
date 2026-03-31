#!/usr/bin/env python3
"""
jlesson — Japanese Lesson Generator CLI

Subcommand groups:
  vocab       Manage vocabulary (list, create, generate-prompt)
  lesson      Run and manage lessons (next, prompt)
  curriculum  View curriculum progress

Entry point: jlesson (defined in pyproject.toml)
"""

from __future__ import annotations

import json
import random
from pathlib import Path

import click

from .curriculum import load_curriculum
from .curriculum import summary as curriculum_summary
from .language_config import get_language_config
from .prompt_template import (
    DIMENSIONS_BEGINNER,
    GRAMMAR_PATTERNS_BEGINNER,
    PERSONS_BEGINNER,
    build_lesson_prompt,
    build_vocab_prompt,
)

VOCAB_DIR = Path(__file__).parent.parent / "vocab"
DEFAULT_CURRICULUM_PATH = Path(__file__).parent.parent / "curriculum" / "curriculum.json"

LANGUAGE_OPTION = click.option(
    "--language",
    default="eng-jap",
    show_default=True,
    type=click.Choice(["eng-jap", "hun-eng", "hun-ger"]),
    help="Language pair: eng-jap (default), hun-eng, or hun-ger.",
)


def _friendly_error(exc: Exception) -> str:
    """Convert LLM / network exceptions into a one-line user message."""
    name = type(exc).__name__
    msg = str(exc)
    # openai SDK exceptions
    if "TimeoutError" in name or "timeout" in msg.lower():
        return (
            "LLM request timed out. The model may need more time for large "
            "prompts.\nTry: set LLM_REQUEST_TIMEOUT to a higher value in .env "
            "(current default: 120s)."
        )
    if "ConnectionError" in name or "Connection" in name:
        from .config import LLM_BASE_URL
        return f"Cannot connect to LLM server at {LLM_BASE_URL}. Is it running?"
    if "RateLimitError" in name:
        return "LLM rate limit exceeded. Wait a moment and retry."
    if "APIError" in name:
        return f"LLM API error: {msg}"
    if isinstance(exc, ValueError):
        return str(exc)
    return f"{name}: {msg}"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _list_themes(vocab_dir: Path | None = None) -> list[str]:
    d = vocab_dir or VOCAB_DIR
    return sorted(p.stem for p in d.glob("*.json"))


def _load_vocab(theme: str, vocab_dir: Path | None = None) -> dict:
    d = vocab_dir or VOCAB_DIR
    path = d / f"{theme}.json"
    if not path.exists():
        available = ", ".join(_list_themes(d)) or "(none)"
        raise click.ClickException(f"theme '{theme}' not found. Available: {available}")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _pick_items(items: list[dict], count: int, shuffle: bool = True) -> list[dict]:
    if count >= len(items):
        return list(items)
    pool = list(items)
    if shuffle:
        random.shuffle(pool)
    return pool[:count]


# ---------------------------------------------------------------------------
# Root group
# ---------------------------------------------------------------------------

@click.group()
def cli() -> None:
    """Japanese Lesson Generator — vocabulary, lessons, and video materials."""


# ---------------------------------------------------------------------------
# vocab subgroup
# ---------------------------------------------------------------------------

@cli.group()
def vocab() -> None:
    """Manage vocabulary files."""


@vocab.command("list")
@LANGUAGE_OPTION
def vocab_list(language: str) -> None:
    """List available vocabulary themes."""
    vocab_dir = Path(__file__).parent.parent / get_language_config(language).vocab_dir
    themes = _list_themes(vocab_dir)
    if themes:
        click.echo("Available themes:")
        for t in themes:
            click.echo(f"  - {t}")
    else:
        click.echo(f"No themes found. Add JSON files to: {vocab_dir}")


@vocab.command("create")
@click.argument("theme")
@click.option("--count", type=int, default=None, help="Total words to generate (nouns + verbs + adjectives).")
@click.option("--nouns", type=int, default=None, help="Noun count (exact if no --count, minimum if --count is set).")
@click.option("--verbs", type=int, default=None, help="Verb count (exact if no --count, minimum if --count is set).")
@click.option("--adjectives", type=int, default=None, help="Adjective count (exact if no --count, minimum if --count is set).")
@click.option("--force", is_flag=True, default=False, help="Overwrite existing theme file if it already exists.")
@click.option(
    "--level",
    default="beginner",
    show_default=True,
    type=click.Choice(["beginner", "intermediate", "advanced"]),
    help="Difficulty level.",
)
@LANGUAGE_OPTION
def vocab_create(
    theme: str,
    count: int | None,
    nouns: int | None,
    verbs: int | None,
    adjectives: int | None,
    force: bool,
    level: str,
    language: str,
) -> None:
    """Generate vocabulary for THEME via LLM and save to vocab/<THEME>.json."""
    from .vocab_generator import generate_vocab
    lang_cfg = get_language_config(language)
    output_dir = Path(__file__).parent.parent / lang_cfg.vocab_dir
    try:
        generate_vocab(
            theme=theme,
            num_nouns=nouns,
            num_verbs=verbs,
            num_adjectives=adjectives,
            total_count=count,
            level=level,
            output_dir=output_dir, language=language, allow_overwrite=force,
        )
    except Exception as exc:
        raise click.ClickException(_friendly_error(exc)) from exc


@vocab.command("extend")
@click.argument("theme")
@click.option("--count", type=int, default=None, help="Total additional words to generate (nouns + verbs + adjectives).")
@click.option("--nouns", type=int, default=None, help="Additional noun count (exact if no --count, minimum if --count is set).")
@click.option("--verbs", type=int, default=None, help="Additional verb count (exact if no --count, minimum if --count is set).")
@click.option("--adjectives", type=int, default=None, help="Additional adjective count (exact if no --count, minimum if --count is set).")
@click.option(
    "--level",
    default="beginner",
    show_default=True,
    type=click.Choice(["beginner", "intermediate", "advanced"]),
    help="Difficulty level for newly generated items.",
)
@LANGUAGE_OPTION
def vocab_extend(
    theme: str,
    count: int | None,
    nouns: int | None,
    verbs: int | None,
    adjectives: int | None,
    level: str,
    language: str,
) -> None:
    """Extend an existing theme by generating and merging additional vocab."""
    from .vocab_generator import extend_vocab

    lang_cfg = get_language_config(language)
    output_dir = Path(__file__).parent.parent / lang_cfg.vocab_dir
    try:
        extend_vocab(
            theme=theme,
            add_nouns=nouns,
            add_verbs=verbs,
            add_adjectives=adjectives,
            total_count=count,
            level=level,
            output_dir=output_dir,
            language=language,
        )
    except Exception as exc:
        raise click.ClickException(_friendly_error(exc)) from exc


@vocab.command("generate-prompt")
@click.argument("theme")
@click.option("--nouns", default=12, show_default=True, help="Number of nouns.")
@click.option("--verbs", default=10, show_default=True, help="Number of verbs.")
@click.option(
    "--level",
    default="beginner",
    show_default=True,
    type=click.Choice(["beginner", "intermediate", "advanced"]),
    help="Difficulty level.",
)
@click.option("--output", "-o", type=click.Path(), default=None, help="Write to file instead of stdout.")
@LANGUAGE_OPTION
def vocab_generate_prompt(theme: str, nouns: int, verbs: int, level: str, output: str | None, language: str) -> None:
    """Print the LLM prompt for generating vocabulary for THEME (no LLM call)."""
    if language == "hun-eng":
        from .prompt_template import hungarian_build_vocab_prompt
        prompt = hungarian_build_vocab_prompt(theme=theme, num_nouns=nouns, num_verbs=verbs, level=level)
    else:
        prompt = build_vocab_prompt(theme=theme, num_nouns=nouns, num_verbs=verbs, level=level)
    if output:
        Path(output).write_text(prompt, encoding="utf-8")
        click.echo(f"Prompt written to: {output}", err=True)
    else:
        click.echo(prompt)


# ---------------------------------------------------------------------------
# lesson subgroup
# ---------------------------------------------------------------------------

@cli.group()
def lesson() -> None:
    """Generate and manage lessons."""


def _run_lesson_generation(
    *,
    theme: str,
    nouns: int,
    verbs: int,
    sentences: int,
    grammar_points: int,
    grammar_points_per_block: int,
    blocks: int,
    seed: int | None,
    curriculum_path: str | None,
    output_dir: str | None,
    no_video: bool,
    no_cache: bool,
    dry_run: bool,
    profile: str,
    narrative: tuple[str, ...],
    narrative_file: Path | None,
    retrieval: bool,
    retrieval_store: Path | None,
    retrieval_backend: str,
    retrieval_embedding_model: str,
    retrieval_min_coverage: float,
    language: str,
    regenerate_lesson_id: int | None,
) -> None:
    """Run lesson generation, optionally overwriting an existing lesson ID."""
    from .lesson_pipeline import LessonConfig, run_pipeline

    lang_cfg = get_language_config(language)
    resolved_curriculum = (
        Path(curriculum_path) if curriculum_path
        else Path(__file__).parent.parent / lang_cfg.curriculum_file
    )
    narrative_blocks = [text.strip() for text in narrative if text.strip()]
    if narrative_file is not None:
        file_text = narrative_file.read_text(encoding="utf-8")
        file_blocks = [block.strip() for block in file_text.split("\n---\n") if block.strip()]
        narrative_blocks.extend(file_blocks)
    config = LessonConfig(
        theme=theme,
        curriculum_path=resolved_curriculum,
        output_dir=Path(output_dir) if output_dir else None,
        num_nouns=nouns,
        num_verbs=verbs,
        sentences_per_grammar=sentences,
        grammar_points_per_lesson=grammar_points,
        grammar_points_per_block=grammar_points_per_block,
        lesson_blocks=blocks,
        seed=seed,
        use_cache=not no_cache,
        render_video=not no_video,
        dry_run=dry_run,
        profile=profile,
        language=language,
        narrative=narrative_blocks,
        retrieval_enabled=retrieval,
        retrieval_store_path=retrieval_store,
        retrieval_backend=retrieval_backend,
        retrieval_embedding_model=retrieval_embedding_model,
        retrieval_min_coverage=retrieval_min_coverage,
        regenerate_lesson_id=regenerate_lesson_id,
    )
    try:
        run_pipeline(config)
    except Exception as exc:
        raise click.ClickException(_friendly_error(exc)) from exc


@lesson.command("add")
@click.option("--theme", "-t", required=True, help="Vocabulary theme for this lesson.")
@click.option("--nouns", default=4, show_default=True, help="Nouns per lesson.")
@click.option("--verbs", default=3, show_default=True, help="Verbs per lesson.")
@click.option("--sentences", default=3, show_default=True, help="Sentences per grammar point.")
@click.option(
    "--grammar-points",
    default=2,
    show_default=True,
    type=click.IntRange(1),
    help="How many grammar progression points to include in the lesson.",
)
@click.option(
    "--grammar-points-per-block",
    default=1,
    show_default=True,
    type=click.IntRange(1),
    help="How many grammar points each block should actively practice from the lesson progression.",
)
@click.option(
    "--blocks",
    default=1,
    show_default=True,
    type=click.IntRange(1),
    help="Generate this many fresh content blocks within the lesson.",
)
@click.option("--seed", type=int, default=None, help="Random seed for reproducible vocab selection.")
@click.option(
    "--curriculum",
    "curriculum_path",
    default=None,
    type=click.Path(),
    help="Path to curriculum JSON (default: curriculum/curriculum.json).",
)
@click.option(
    "--output-dir",
    default=None,
    type=click.Path(),
    help="Output directory (default: output/).",
)
@click.option("--no-video", is_flag=True, default=False, help="Skip video rendering.")
@click.option("--no-cache", is_flag=True, default=False, help="Disable LLM response cache (always call LLM).")
@click.option("--dry-run", is_flag=True, default=False, help="Skip TTS/card/video — generate content and report only.")
@click.option(
    "--profile",
    default="passive_video",
    show_default=True,
    type=click.Choice(["passive_video", "active_flash_cards", "simple_listen"]),
    help="Touch profile for asset compilation and video rendering.",
)
@click.option(
    "--narrative",
    multiple=True,
    help="Optional block narrative. Repeat the option to provide a progression across blocks.",
)
@click.option(
    "--narrative-file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="Path to a text file with story context for sentence generation.",
)
@click.option(
    "--retrieval/--no-retrieval",
    default=True,
    show_default=True,
    help="Enable retrieval before the current generation flow.",
)
@click.option(
    "--retrieval-store",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Path to a JSON retrieval store.",
)
@click.option(
    "--retrieval-backend",
    default="file",
    show_default=True,
    type=click.Choice(["file", "chroma"]),
    help="Retrieval backend implementation.",
)
@click.option(
    "--retrieval-embedding-model",
    default="text-embedding-3-small",
    show_default=True,
    help="Embedding model used by vector retrieval backends.",
)
@click.option(
    "--retrieval-min-coverage",
    type=float,
    default=0.6,
    show_default=True,
    help="Minimum retrieval coverage required before retrieved material is used.",
)
@LANGUAGE_OPTION
def lesson_add(
    theme: str,
    nouns: int,
    verbs: int,
    sentences: int,
    grammar_points: int,
    grammar_points_per_block: int,
    blocks: int,
    seed: int | None,
    curriculum_path: str | None,
    output_dir: str | None,
    no_video: bool,
    no_cache: bool,
    dry_run: bool,
    profile: str,
    narrative: tuple[str, ...],
    narrative_file: Path | None,
    retrieval: bool,
    retrieval_store: Path | None,
    retrieval_backend: str,
    retrieval_embedding_model: str,
    retrieval_min_coverage: float,
    language: str,
) -> None:
    """Run the full pipeline for the next lesson.

    Selects grammar, generates sentences and practice items via LLM,
    persists lesson content, and renders an MP4 video.
    """
    _run_lesson_generation(
        theme=theme,
        nouns=nouns,
        verbs=verbs,
        sentences=sentences,
        grammar_points=grammar_points,
        grammar_points_per_block=grammar_points_per_block,
        blocks=blocks,
        seed=seed,
        curriculum_path=curriculum_path,
        output_dir=output_dir,
        no_video=no_video,
        no_cache=no_cache,
        dry_run=dry_run,
        profile=profile,
        language=language,
        narrative=narrative,
        narrative_file=narrative_file,
        retrieval=retrieval,
        retrieval_store=retrieval_store,
        retrieval_backend=retrieval_backend,
        retrieval_embedding_model=retrieval_embedding_model,
        retrieval_min_coverage=retrieval_min_coverage,
        regenerate_lesson_id=None,
    )


@lesson.command("update")
@click.argument("lesson_id", type=click.IntRange(1))
@click.option("--theme", "-t", default=None, help="Vocabulary theme (required unless --video-only).")
@click.option("--nouns", default=4, show_default=True, help="Nouns per lesson.")
@click.option("--verbs", default=3, show_default=True, help="Verbs per lesson.")
@click.option("--sentences", default=3, show_default=True, help="Sentences per grammar point.")
@click.option(
    "--grammar-points",
    default=2,
    show_default=True,
    type=click.IntRange(1),
    help="How many grammar progression points to include in the lesson.",
)
@click.option(
    "--grammar-points-per-block",
    default=1,
    show_default=True,
    type=click.IntRange(1),
    help="How many grammar points each block should actively practice from the lesson progression.",
)
@click.option(
    "--blocks",
    default=1,
    show_default=True,
    type=click.IntRange(1),
    help="Generate this many fresh content blocks within the lesson.",
)
@click.option("--seed", type=int, default=None, help="Random seed for reproducible vocab selection.")
@click.option(
    "--curriculum",
    "curriculum_path",
    default=None,
    type=click.Path(),
    help="Path to curriculum JSON (default: curriculum/curriculum.json).",
)
@click.option(
    "--output-dir",
    default=None,
    type=click.Path(),
    help="Output directory (default: output/).",
)
@click.option("--no-video", is_flag=True, default=False, help="Skip video rendering (full pipeline only).")
@click.option("--no-cache", is_flag=True, default=False, help="Disable LLM response cache (always call LLM).")
@click.option("--dry-run", is_flag=True, default=False, help="Skip TTS/card/video — generate content and report only.")
@click.option(
    "--profile",
    default="passive_video",
    show_default=True,
    type=click.Choice(["passive_video", "active_flash_cards", "simple_listen"]),
    help="Touch profile for asset compilation and video rendering.",
)
@click.option(
    "--narrative",
    multiple=True,
    help="Optional block narrative. Repeat the option to provide a progression across blocks.",
)
@click.option(
    "--narrative-file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="Path to a text file with story context for sentence generation.",
)
@click.option(
    "--retrieval/--no-retrieval",
    default=True,
    show_default=True,
    help="Enable retrieval before the current generation flow.",
)
@click.option(
    "--retrieval-store",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Path to a JSON retrieval store.",
)
@click.option(
    "--retrieval-backend",
    default="file",
    show_default=True,
    type=click.Choice(["file", "chroma"]),
    help="Retrieval backend implementation.",
)
@click.option(
    "--retrieval-embedding-model",
    default="text-embedding-3-small",
    show_default=True,
    help="Embedding model used by vector retrieval backends.",
)
@click.option(
    "--retrieval-min-coverage",
    type=float,
    default=0.6,
    show_default=True,
    help="Minimum retrieval coverage required before retrieved material is used.",
)
@click.option(
    "--video-only",
    is_flag=True,
    default=False,
    help="Render video from stored lesson context only — skip content regeneration.",
)
@click.option(
    "--recompile-cards",
    is_flag=True,
    default=False,
    help="Recompile card images from lesson content before rendering (--video-only only).",
)
@LANGUAGE_OPTION
def lesson_update(
    lesson_id: int,
    theme: str | None,
    nouns: int,
    verbs: int,
    sentences: int,
    grammar_points: int,
    grammar_points_per_block: int,
    blocks: int,
    seed: int | None,
    curriculum_path: str | None,
    output_dir: str | None,
    no_video: bool,
    no_cache: bool,
    dry_run: bool,
    profile: str,
    narrative: tuple[str, ...],
    narrative_file: Path | None,
    retrieval: bool,
    retrieval_store: Path | None,
    retrieval_backend: str,
    retrieval_embedding_model: str,
    retrieval_min_coverage: float,
    video_only: bool,
    recompile_cards: bool,
    language: str,
) -> None:
    """Run or re-render an existing lesson ID.

    Without --video-only: re-runs the full generation pipeline for LESSON_ID
    (requires --theme).

    With --video-only: loads the stored lesson context from content.json and
    renders the video without regenerating any content.
    """
    if video_only:
        from .lesson_pipeline import render_existing_lesson
        try:
            video_path = render_existing_lesson(
                lesson_id=lesson_id,
                output_dir=Path(output_dir) if output_dir else None,
                theme=theme or "",
                profile=profile,
                recompile_cards=recompile_cards,
                language=language,
                verbose=True,
            )
            click.echo(f"Video rendered: {video_path}")
        except Exception as exc:
            raise click.ClickException(_friendly_error(exc)) from exc
    else:
        if not theme:
            raise click.UsageError("--theme is required unless --video-only is set.")
        _run_lesson_generation(
            theme=theme,
            nouns=nouns,
            verbs=verbs,
            sentences=sentences,
            grammar_points=grammar_points,
            grammar_points_per_block=grammar_points_per_block,
            blocks=blocks,
            seed=seed,
            curriculum_path=curriculum_path,
            output_dir=output_dir,
            no_video=no_video,
            no_cache=no_cache,
            dry_run=dry_run,
            profile=profile,
            narrative=narrative,
            narrative_file=narrative_file,
            retrieval=retrieval,
            retrieval_store=retrieval_store,
            retrieval_backend=retrieval_backend,
            retrieval_embedding_model=retrieval_embedding_model,
            retrieval_min_coverage=retrieval_min_coverage,
            language=language,
            regenerate_lesson_id=lesson_id,
        )


# kept for backward compatibility
@lesson.command("regenerate", hidden=True, deprecated=True)
@click.argument("lesson_id", type=click.IntRange(1))
@click.option("--theme", "-t", required=True, help="Vocabulary theme for this lesson.")
@click.option("--nouns", default=4, show_default=True, help="Nouns per lesson.")
@click.option("--verbs", default=3, show_default=True, help="Verbs per lesson.")
@click.option("--sentences", default=3, show_default=True, help="Sentences per grammar point.")
@click.option("--grammar-points", default=2, show_default=True, type=click.IntRange(1))
@click.option("--grammar-points-per-block", default=1, show_default=True, type=click.IntRange(1))
@click.option("--blocks", default=1, show_default=True, type=click.IntRange(1))
@click.option("--seed", type=int, default=None)
@click.option("--curriculum", "curriculum_path", default=None, type=click.Path())
@click.option("--output-dir", default=None, type=click.Path())
@click.option("--no-video", is_flag=True, default=False)
@click.option("--no-cache", is_flag=True, default=False)
@click.option("--dry-run", is_flag=True, default=False)
@click.option("--profile", default="passive_video", show_default=True, type=click.Choice(["passive_video", "active_flash_cards", "simple_listen"]))
@click.option("--narrative", multiple=True)
@click.option("--narrative-file", type=click.Path(exists=True, dir_okay=False, path_type=Path), default=None)
@click.option("--retrieval/--no-retrieval", default=True, show_default=True)
@click.option("--retrieval-store", type=click.Path(dir_okay=False, path_type=Path), default=None)
@click.option("--retrieval-backend", default="file", show_default=True, type=click.Choice(["file", "chroma"]))
@click.option("--retrieval-embedding-model", default="text-embedding-3-small", show_default=True)
@click.option("--retrieval-min-coverage", type=float, default=0.6, show_default=True)
@LANGUAGE_OPTION
def lesson_regenerate(lesson_id, theme, nouns, verbs, sentences, grammar_points, grammar_points_per_block, blocks, seed, curriculum_path, output_dir, no_video, no_cache, dry_run, profile, narrative, narrative_file, retrieval, retrieval_store, retrieval_backend, retrieval_embedding_model, retrieval_min_coverage, language):
    """Deprecated: use `lesson update LESSON_ID --theme THEME` instead."""
    _run_lesson_generation(
        theme=theme, nouns=nouns, verbs=verbs, sentences=sentences,
        grammar_points=grammar_points, grammar_points_per_block=grammar_points_per_block,
        blocks=blocks, seed=seed, curriculum_path=curriculum_path, output_dir=output_dir,
        no_video=no_video, no_cache=no_cache, dry_run=dry_run, profile=profile,
        narrative=narrative, narrative_file=narrative_file, retrieval=retrieval,
        retrieval_store=retrieval_store, retrieval_backend=retrieval_backend,
        retrieval_embedding_model=retrieval_embedding_model,
        retrieval_min_coverage=retrieval_min_coverage, language=language,
        regenerate_lesson_id=lesson_id,
    )


# kept for backward compatibility
@lesson.command("render", hidden=True, deprecated=True)
@click.argument("lesson_id", type=int)
@click.option("--output-dir", default=None, type=click.Path())
@click.option("--theme", default="", show_default=False)
@click.option("--profile", default="passive_video", show_default=True, type=click.Choice(["passive_video", "active_flash_cards", "simple_listen"]))
@click.option("--recompile-cards", is_flag=True, default=False)
@LANGUAGE_OPTION
def lesson_render(lesson_id, output_dir, theme, profile, recompile_cards, language):
    """Deprecated: use `lesson update LESSON_ID --video-only` instead."""
    from .lesson_pipeline import render_existing_lesson

    try:
        video_path = render_existing_lesson(
            lesson_id=lesson_id,
            output_dir=Path(output_dir) if output_dir else None,
            theme=theme,
            profile=profile,
            recompile_cards=recompile_cards,
            language=language,
            verbose=True,
        )
        click.echo(f"Video rendered: {video_path}")
    except Exception as exc:
        raise click.ClickException(_friendly_error(exc)) from exc


# kept for backward compatibility
@lesson.command("next", hidden=True, deprecated=True)
@click.option("--theme", "-t", required=True)
@click.option("--nouns", default=4, show_default=True)
@click.option("--verbs", default=3, show_default=True)
@click.option("--sentences", default=3, show_default=True)
@click.option("--grammar-points", default=2, show_default=True, type=click.IntRange(1))
@click.option("--grammar-points-per-block", default=1, show_default=True, type=click.IntRange(1))
@click.option("--blocks", default=1, show_default=True, type=click.IntRange(1))
@click.option("--seed", type=int, default=None)
@click.option("--curriculum", "curriculum_path", default=None, type=click.Path())
@click.option("--output-dir", default=None, type=click.Path())
@click.option("--no-video", is_flag=True, default=False)
@click.option("--no-cache", is_flag=True, default=False)
@click.option("--dry-run", is_flag=True, default=False)
@click.option("--profile", default="passive_video", show_default=True, type=click.Choice(["passive_video", "active_flash_cards", "simple_listen"]))
@click.option("--narrative", multiple=True)
@click.option("--narrative-file", type=click.Path(exists=True, dir_okay=False, path_type=Path), default=None)
@click.option("--retrieval/--no-retrieval", default=True, show_default=True)
@click.option("--retrieval-store", type=click.Path(dir_okay=False, path_type=Path), default=None)
@click.option("--retrieval-backend", default="file", show_default=True, type=click.Choice(["file", "chroma"]))
@click.option("--retrieval-embedding-model", default="text-embedding-3-small", show_default=True)
@click.option("--retrieval-min-coverage", type=float, default=0.6, show_default=True)
@LANGUAGE_OPTION
def lesson_next(theme, nouns, verbs, sentences, grammar_points, grammar_points_per_block, blocks, seed, curriculum_path, output_dir, no_video, no_cache, dry_run, profile, narrative, narrative_file, retrieval, retrieval_store, retrieval_backend, retrieval_embedding_model, retrieval_min_coverage, language):
    """Deprecated: use `lesson add --theme THEME` instead."""
    _run_lesson_generation(
        theme=theme, nouns=nouns, verbs=verbs, sentences=sentences,
        grammar_points=grammar_points, grammar_points_per_block=grammar_points_per_block,
        blocks=blocks, seed=seed, curriculum_path=curriculum_path, output_dir=output_dir,
        no_video=no_video, no_cache=no_cache, dry_run=dry_run, profile=profile,
        narrative=narrative, narrative_file=narrative_file, retrieval=retrieval,
        retrieval_store=retrieval_store, retrieval_backend=retrieval_backend,
        retrieval_embedding_model=retrieval_embedding_model,
        retrieval_min_coverage=retrieval_min_coverage, language=language,
        regenerate_lesson_id=None,
    )


# kept for backward compatibility
@lesson.command("run", hidden=True, deprecated=True)
@click.argument("lesson_id", type=click.IntRange(1))
@click.option("--theme", "-t", default=None)
@click.option("--nouns", default=4, show_default=True)
@click.option("--verbs", default=3, show_default=True)
@click.option("--sentences", default=3, show_default=True)
@click.option("--grammar-points", default=2, show_default=True, type=click.IntRange(1))
@click.option("--grammar-points-per-block", default=1, show_default=True, type=click.IntRange(1))
@click.option("--blocks", default=1, show_default=True, type=click.IntRange(1))
@click.option("--seed", type=int, default=None)
@click.option("--curriculum", "curriculum_path", default=None, type=click.Path())
@click.option("--output-dir", default=None, type=click.Path())
@click.option("--no-video", is_flag=True, default=False)
@click.option("--no-cache", is_flag=True, default=False)
@click.option("--dry-run", is_flag=True, default=False)
@click.option("--profile", default="passive_video", show_default=True, type=click.Choice(["passive_video", "active_flash_cards", "simple_listen"]))
@click.option("--narrative", multiple=True)
@click.option("--narrative-file", type=click.Path(exists=True, dir_okay=False, path_type=Path), default=None)
@click.option("--retrieval/--no-retrieval", default=True, show_default=True)
@click.option("--retrieval-store", type=click.Path(dir_okay=False, path_type=Path), default=None)
@click.option("--retrieval-backend", default="file", show_default=True, type=click.Choice(["file", "chroma"]))
@click.option("--retrieval-embedding-model", default="text-embedding-3-small", show_default=True)
@click.option("--retrieval-min-coverage", type=float, default=0.6, show_default=True)
@click.option("--video-only", is_flag=True, default=False)
@click.option("--recompile-cards", is_flag=True, default=False)
@LANGUAGE_OPTION
def lesson_run_compat(lesson_id, theme, nouns, verbs, sentences, grammar_points, grammar_points_per_block, blocks, seed, curriculum_path, output_dir, no_video, no_cache, dry_run, profile, narrative, narrative_file, retrieval, retrieval_store, retrieval_backend, retrieval_embedding_model, retrieval_min_coverage, video_only, recompile_cards, language):
    """Deprecated: use `lesson update LESSON_ID` instead."""
    if video_only:
        from .lesson_pipeline import render_existing_lesson
        try:
            video_path = render_existing_lesson(
                lesson_id=lesson_id,
                output_dir=Path(output_dir) if output_dir else None,
                theme=theme or "",
                profile=profile,
                recompile_cards=recompile_cards,
                language=language,
                verbose=True,
            )
            click.echo(f"Video rendered: {video_path}")
        except Exception as exc:
            raise click.ClickException(_friendly_error(exc)) from exc
    else:
        if not theme:
            raise click.UsageError("--theme is required unless --video-only is set.")
        _run_lesson_generation(
            theme=theme, nouns=nouns, verbs=verbs, sentences=sentences,
            grammar_points=grammar_points, grammar_points_per_block=grammar_points_per_block,
            blocks=blocks, seed=seed, curriculum_path=curriculum_path, output_dir=output_dir,
            no_video=no_video, no_cache=no_cache, dry_run=dry_run, profile=profile,
            narrative=narrative, narrative_file=narrative_file, retrieval=retrieval,
            retrieval_store=retrieval_store, retrieval_backend=retrieval_backend,
            retrieval_embedding_model=retrieval_embedding_model,
            retrieval_min_coverage=retrieval_min_coverage, language=language,
            regenerate_lesson_id=lesson_id,
        )


@lesson.command("prompt")
@click.argument("theme")
@click.option("--nouns", "-n", default=6, show_default=True, help="Number of nouns.")
@click.option("--verbs", "-v", default=6, show_default=True, help="Number of verbs.")
@click.option("--seed", "-s", type=int, default=None, help="Random seed.")
@click.option("--no-shuffle", is_flag=True, default=False, help="Pick first N items without shuffling.")
@click.option("--output", "-o", type=click.Path(), default=None, help="Write to file instead of stdout.")
@LANGUAGE_OPTION
def lesson_prompt(
    theme: str,
    nouns: int,
    verbs: int,
    seed: int | None,
    no_shuffle: bool,
    output: str | None,
    language: str,
) -> None:
    """Generate a lesson prompt text for THEME (no LLM call, no pipeline)."""
    if seed is not None:
        random.seed(seed)
    lang_cfg = get_language_config(language)
    vocab_dir = Path(__file__).parent.parent / lang_cfg.vocab_dir
    vocab = _load_vocab(theme, vocab_dir)
    selected_nouns = _pick_items(vocab["nouns"], nouns, shuffle=not no_shuffle)
    selected_verbs = _pick_items(vocab["verbs"], verbs, shuffle=not no_shuffle)
    if language == "hun-eng":
        from .prompt_template import hungarian_build_lesson_prompt
        prompt = hungarian_build_lesson_prompt(
            theme=theme,
            nouns=selected_nouns,
            verbs=selected_verbs,
        )
    else:
        prompt = build_lesson_prompt(
            theme=theme,
            nouns=selected_nouns,
            verbs=selected_verbs,
            persons=PERSONS_BEGINNER,
            grammar_patterns=GRAMMAR_PATTERNS_BEGINNER,
            dimensions=DIMENSIONS_BEGINNER,
        )
    if output:
        Path(output).write_text(prompt, encoding="utf-8")
        click.echo(f"Prompt written to: {output}", err=True)
    else:
        click.echo(prompt)


# ---------------------------------------------------------------------------
# curriculum subgroup
# ---------------------------------------------------------------------------

@cli.group()
def curriculum() -> None:
    """View curriculum progress."""


@curriculum.command("show")
@click.option(
    "--curriculum",
    "curriculum_path",
    default=None,
    type=click.Path(),
    help="Path to curriculum JSON (default: curriculum/curriculum.json).",
)
@LANGUAGE_OPTION
def curriculum_show(curriculum_path: str | None, language: str) -> None:
    """Display the current curriculum progress."""
    if curriculum_path:
        path = Path(curriculum_path)
    else:
        path = Path(__file__).parent.parent / get_language_config(language).curriculum_file
    cur = load_curriculum(path)
    click.echo(curriculum_summary(cur))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    cli()
