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
    type=click.Choice(["eng-jap", "hun-eng", "hun-ger", "eng-fre"]),
    help="Language pair: eng-jap (default), hun-eng, hun-ger, or eng-fre.",
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
    elif language == "eng-fre":
        from .prompt_template import french_build_vocab_prompt
        prompt = french_build_vocab_prompt(theme=theme, num_nouns=nouns, num_verbs=verbs, level=level)
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
    adjectives: int,
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
    subtitle_file: Path | None,
    retrieval: bool,
    retrieval_store: Path | None,
    retrieval_backend: str,
    retrieval_embedding_model: str,
    retrieval_min_coverage: float,
    language: str,
    regenerate_lesson_id: int | None,
    from_step: str | None = None,
    rcm_path: Path | None = None,
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
        num_adjectives=adjectives,
        sentences_per_grammar=sentences / grammar_points_per_block if grammar_points_per_block else sentences,
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
        subtitle_file=subtitle_file,
        retrieval_enabled=retrieval,
        retrieval_store_path=retrieval_store,
        retrieval_backend=retrieval_backend,
        retrieval_embedding_model=retrieval_embedding_model,
        retrieval_min_coverage=retrieval_min_coverage,
        regenerate_lesson_id=regenerate_lesson_id,
        from_step=from_step,
        rcm_path=rcm_path,
    )
    try:
        run_pipeline(config)
    except Exception as exc:
        raise click.ClickException(_friendly_error(exc)) from exc


@lesson.command("add")
@click.option("--theme", "-t", required=True, help="Vocabulary theme for this lesson.")
@click.option("--nouns", default=4, show_default=True, help="Nouns per block.")
@click.option("--verbs", default=3, show_default=True, help="Verbs per block.")
@click.option("--adjectives", default=1, show_default=True, help="Adjectives per block.")
@click.option("--sentences", default=4, show_default=True, help="Sentences per grammar point.")
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
    default="simple_listen",
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
    "--subtitle-file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="Path to an SRT subtitle file; the LLM will synthesise narrative blocks from the full script.",
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
    "--rcm-path",
    type=click.Path(path_type=Path),
    default=None,
    help="Path to the RCM store directory. Enables cross-lesson item reuse and asset caching.",
)
@LANGUAGE_OPTION
def lesson_add(
    theme: str,
    nouns: int,
    verbs: int,
    adjectives: int,
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
    subtitle_file: Path | None,
    retrieval: bool,
    retrieval_store: Path | None,
    retrieval_backend: str,
    retrieval_embedding_model: str,
    retrieval_min_coverage: float,
    language: str,
    rcm_path: Path | None,
) -> None:
    """Run the full pipeline for the next lesson.

    Selects grammar, generates sentences and practice items via LLM,
    persists lesson content, and renders an MP4 video.
    """
    _run_lesson_generation(
        theme=theme,
        nouns=nouns,
        verbs=verbs,
        adjectives=adjectives,
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
        subtitle_file=subtitle_file,
        retrieval=retrieval,
        retrieval_store=retrieval_store,
        retrieval_backend=retrieval_backend,
        retrieval_embedding_model=retrieval_embedding_model,
        retrieval_min_coverage=retrieval_min_coverage,
        regenerate_lesson_id=None,
        rcm_path=rcm_path,
    )


@lesson.command("update")
@click.argument("lesson_id", type=click.IntRange(1))
@click.option("--theme", "-t", default=None, help="Vocabulary theme (required unless --video-only).")
@click.option("--nouns", default=4, show_default=True, help="Nouns per block.")
@click.option("--verbs", default=3, show_default=True, help="Verbs per block.")
@click.option("--adjectives", default=1, show_default=True, help="Adjectives per block.")
@click.option("--sentences", default=4, show_default=True, help="Sentences per grammar point.")
@click.option(
    "--grammar-points",
    default=3,
    show_default=True,
    type=click.IntRange(1),
    help="How many grammar progression points to include in the lesson.",
)
@click.option(
    "--grammar-points-per-block",
    default=2,
    show_default=True,
    type=click.IntRange(1),
    help="How many grammar points each block should actively practice from the lesson progression.",
)
@click.option(
    "--blocks",
    default=5,
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
    "--subtitle-file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="Path to an SRT subtitle file; the LLM will synthesise narrative blocks from the full script.",
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
    "--from-step",
    "from_step",
    default=None,
    type=click.Choice(["compile_assets", "compile_touches", "render_video"]),
    help=(
        "Resume from a specific render step using the stored lesson checkpoint "
        "(skips content regeneration). "
        "'render_video' wires existing assets and re-renders; "
        "'compile_assets' recompiles cards and TTS before rendering."
    ),
)
@click.option(
    "--rcm-path",
    type=click.Path(path_type=Path),
    default=None,
    help="Path to the RCM store directory. Enables cross-lesson item reuse and asset caching.",
)
@LANGUAGE_OPTION
def lesson_update(
    lesson_id: int,
    theme: str | None,
    nouns: int,
    verbs: int,
    adjectives: int,
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
    subtitle_file: Path | None,
    retrieval: bool,
    retrieval_store: Path | None,
    retrieval_backend: str,
    retrieval_embedding_model: str,
    retrieval_min_coverage: float,
    from_step: str | None,
    language: str,
    rcm_path: Path | None,
) -> None:
    """Run or re-render an existing lesson ID.

    Without --from-step: re-runs the full generation pipeline for LESSON_ID
    (requires --theme).

    With --from-step: loads the stored lesson checkpoint and runs only the
    render sub-pipeline (compile_assets / render_video).
    """
    if from_step is not None:
        _run_lesson_generation(
            theme=theme or "",
            nouns=nouns,
            verbs=verbs,
            adjectives=adjectives,
            sentences=sentences,
            grammar_points=grammar_points,
            grammar_points_per_block=grammar_points_per_block,
            blocks=blocks,
            seed=seed,
            curriculum_path=curriculum_path,
            output_dir=output_dir,
            no_video=False,
            no_cache=no_cache,
            dry_run=dry_run,
            profile=profile,
            narrative=narrative,
            narrative_file=narrative_file,
            subtitle_file=subtitle_file,
            retrieval=retrieval,
            retrieval_store=retrieval_store,
            retrieval_backend=retrieval_backend,
            retrieval_embedding_model=retrieval_embedding_model,
            retrieval_min_coverage=retrieval_min_coverage,
            language=language,
            regenerate_lesson_id=lesson_id,
            from_step=from_step,
            rcm_path=rcm_path,
        )
    else:
        if not theme:
            raise click.UsageError("--theme is required unless --from-step is set.")
        _run_lesson_generation(
            theme=theme,
            nouns=nouns,
            verbs=verbs,
            adjectives=adjectives,
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
            subtitle_file=subtitle_file,
            retrieval=retrieval,
            retrieval_store=retrieval_store,
            retrieval_backend=retrieval_backend,
            retrieval_embedding_model=retrieval_embedding_model,
            retrieval_min_coverage=retrieval_min_coverage,
            language=language,
            regenerate_lesson_id=lesson_id,
            rcm_path=rcm_path,
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
    elif language == "eng-fre":
        from .prompt_template import french_build_lesson_prompt
        prompt = french_build_lesson_prompt(
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
# lesson shorts
# ---------------------------------------------------------------------------

@lesson.command("shorts")
@click.option(
    "--lesson-dir",
    "lesson_dir",
    required=True,
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Path to the lesson_NNN output folder (contains cards/, audio/, steps/).",
)
@click.option(
    "--blocks",
    default=5,
    show_default=True,
    type=click.IntRange(1),
    help="Number of blocks to render as Shorts (first N blocks).",
)
@click.option(
    "--block-list",
    "block_list",
    default=None,
    help="Comma-separated list of block indices to render, e.g. '1,3,5'. Overrides --blocks.",
)
@click.option(
    "--pause-card",
    "pause_after",
    default=1.0,
    show_default=True,
    type=float,
    help="Pause in seconds after audio on each card.",
)
@click.option(
    "--fps",
    default=30,
    show_default=True,
    type=click.IntRange(1),
    help="Output frames per second.",
)
def lesson_shorts(
    lesson_dir: Path,
    blocks: int,
    block_list: str | None,
    pause_after: float,
    fps: int,
) -> None:
    """Render lesson blocks as vertical 9:16 YouTube Shorts.

    Each Short is one block: vocab nouns → verbs → adjectives → grammar
    sentences assembled into a 1080×1920 MP4 (≤60s target).

    Existing cards and audio from LESSON_DIR are reused — no LLM calls,
    no TTS regeneration.

    Output: LESSON_DIR/shorts/short_block_NN.mp4

    \b
    Examples:
      # First 5 blocks
      jlesson lesson shorts --lesson-dir output/kiki/.../lesson_001 --blocks 5

      # Specific blocks
      jlesson lesson shorts --lesson-dir output/kiki/.../lesson_001 --block-list 1,3,5
    """
    import json
    import tempfile

    try:
        from PIL import Image, ImageFilter, ImageEnhance
    except ImportError:
        raise click.ClickException("Pillow not installed. Run: pip install Pillow")

    try:
        import moviepy  # noqa: F401 — validate moviepy is available before starting
    except ImportError:
        raise click.ClickException("moviepy not installed. Run: pip install moviepy")

    from jlesson.video.builder import VideoBuilder

    # --- resolve block indices ---
    if block_list:
        try:
            indices = [int(x.strip()) for x in block_list.split(",")]
        except ValueError:
            raise click.UsageError("--block-list must be comma-separated integers, e.g. '1,3,5'")
    else:
        indices = list(range(1, blocks + 1))

    # --- load planner JSON ---
    planner_path = lesson_dir / "steps" / "canonical_planner" / "output.json"
    if not planner_path.exists():
        raise click.ClickException(f"Planner output not found: {planner_path}")

    with open(planner_path, encoding="utf-8") as f:
        all_blocks = json.load(f)[0]["blocks"]
    block_map = {b["block_index"]: b for b in all_blocks}

    cards_dir = lesson_dir / "cards"
    audio_dir = lesson_dir / "audio"
    shorts_dir = lesson_dir / "shorts"
    shorts_dir.mkdir(exist_ok=True)

    SHORTS_W, SHORTS_H = 1080, 1920
    CARD_W, CARD_H = 1920, 1080

    def _make_vertical_frame(card_path: Path, tmp_dir: Path) -> Path:
        out = tmp_dir / f"{card_path.stem}_v.png"
        if out.exists():
            return out
        img = Image.open(card_path).convert("RGB")
        scale = max(SHORTS_W / CARD_W, SHORTS_H / CARD_H)
        bw, bh = int(CARD_W * scale), int(CARD_H * scale)
        bg = img.resize((bw, bh), Image.LANCZOS)
        left, top = (bw - SHORTS_W) // 2, (bh - SHORTS_H) // 2
        bg = bg.crop((left, top, left + SHORTS_W, top + SHORTS_H))
        bg = bg.filter(ImageFilter.GaussianBlur(radius=20))
        bg = ImageEnhance.Brightness(bg).enhance(0.4)
        fg_w = SHORTS_W
        fg_h = int(CARD_H * (fg_w / CARD_W))
        fg = img.resize((fg_w, fg_h), Image.LANCZOS)
        frame = bg.copy()
        frame.paste(fg, (0, (SHORTS_H - fg_h) // 2))
        frame.save(out)
        return out

    def _build_block_short(block: dict, out_path: Path, tmp_dir: Path) -> None:
        seqs = block["content_sequences"]
        item_ids = [
            item["id"]
            for section in ("nouns", "verbs", "adjectives", "grammar")
            for item in seqs.get(section, [])
        ]
        video_builder = VideoBuilder(fps=fps)
        clips = []
        running_dur = 0.0
        for item_id in item_ids:
            card_path = cards_dir / f"{item_id}_card_en_ja.png"
            if not card_path.exists():
                continue
            if running_dur >= 55.0:
                click.echo(f"  INFO: reached 55s limit, dropping remaining items")
                break
            v_frame = _make_vertical_frame(card_path, tmp_dir)
            audio_en = audio_dir / f"{item_id}_audio_en.mp3"
            audio_ja = audio_dir / f"{item_id}_audio_ja_f.mp3"
            valid_audio = [p for p in [audio_en, audio_ja] if p.exists()]
            clip = video_builder.create_multi_audio_clip(
                v_frame, valid_audio,
                pause_before=0.5, pause_between=0.3, pause_after=pause_after,
            )
            running_dur += clip.duration
            clips.append(clip)

        if not clips:
            click.echo(f"  WARN: no clips for block {block['block_index']}, skipping")
            return

        total = sum(c.duration for c in clips)

        out_path.parent.mkdir(parents=True, exist_ok=True)
        video_builder.build_video(clips, out_path, method="ffmpeg")
        click.echo(f"  Saved: {out_path.name} ({out_path.stat().st_size / (1024*1024):.1f} MB, {total:.1f}s)")

    click.echo(f"Rendering {len(indices)} short(s) → {shorts_dir}")
    with tempfile.TemporaryDirectory(prefix="jlesson_shorts_") as tmp:
        tmp_dir = Path(tmp)
        for idx in indices:
            if idx not in block_map:
                click.echo(f"  WARN: block {idx} not found, skipping")
                continue
            click.echo(f"\nBlock {idx}: {block_map[idx]['narrative']['narrative'][:60]}...")
            out = shorts_dir / f"short_block_{idx:02d}.mp4"
            try:
                _build_block_short(block_map[idx], out, tmp_dir)
            except Exception as exc:
                raise click.ClickException(_friendly_error(exc)) from exc

    click.echo(f"\nDone. Shorts in: {shorts_dir}")


@lesson.command("bundle")
@click.argument(
    "lesson_dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
)
@click.option(
    "--rcm-path",
    required=True,
    type=click.Path(file_okay=False, path_type=Path),
    help="Path to the RCM store directory (same value used with --rcm-path during lesson generation).",
)
@LANGUAGE_OPTION
def lesson_bundle(lesson_dir: Path, rcm_path: Path, language: str) -> None:
    """Copy RCM-stored assets into a lesson folder to make it self-contained.

    LESSON_DIR should be the lesson_NNN folder, e.g.:
      output/eng-fre/01 northern exposure.../lesson_001

    Assets are copied into LESSON_DIR/audio/ and LESSON_DIR/cards/ so the
    folder can be used standalone (for video rendering, archival, or sharing)
    without requiring the RCM store to be present.
    """
    import shutil
    from jlesson.rcm import open_rcm
    from jlesson.asset_compiler import build_asset_suffix_map

    planner_path = lesson_dir / "steps" / "lesson_planner" / "output.json"
    if not planner_path.exists():
        raise click.ClickException(f"Lesson planner output not found: {planner_path}")

    with open(planner_path, encoding="utf-8") as f:
        blocks = json.load(f)

    from jlesson.models import GeneralItem

    items: list[GeneralItem] = []
    for block in blocks:
        for phase_items in block.get("content_sequences", {}).values():
            for raw in phase_items:
                try:
                    items.append(GeneralItem.model_validate(raw))
                except Exception:
                    pass

    audio_dir = lesson_dir / "audio"
    cards_dir = lesson_dir / "cards"
    audio_dir.mkdir(exist_ok=True)
    cards_dir.mkdir(exist_ok=True)

    _SUFFIX = build_asset_suffix_map(language)

    copied = 0
    already_present = 0
    missing = 0

    with open_rcm(rcm_path) as store:
        for item in items:
            if not item.canonical or not item.canonical.id:
                continue
            item_id = item.canonical.id
            for key, suffix in _SUFFIX.items():
                dest_dir = audio_dir if "audio" in key else cards_dir
                dest = dest_dir / f"{item_id}_{suffix}"
                if dest.exists():
                    already_present += 1
                    continue
                src_path = store.get_asset(item_id, language, key)
                if src_path is None:
                    missing += 1
                    continue
                shutil.copy2(src_path, dest)
                copied += 1

    click.echo(f"Bundle complete for: {lesson_dir.name}")
    click.echo(f"  Copied          : {copied}")
    click.echo(f"  Already present : {already_present}")
    click.echo(f"  Not in store    : {missing}")


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
