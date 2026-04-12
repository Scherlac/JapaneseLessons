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
import os
from pathlib import Path

import click

from .curriculum import load_curriculum
from .curriculum import summary as curriculum_summary
from .language_config import get_language_config
# load env variables from .env (e.g. LLM API keys, RCM path)
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

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

    # Resolve the RCM path: explicit arg > env var > central default ~/.jlesson/rcm
    if rcm_path is None:
        env_rcm = os.environ.get("JLESSON_RCM_PATH")
        rcm_path = Path(env_rcm) if env_rcm else Path.home() / ".jlesson" / "rcm"

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
# rcm subgroup
# ---------------------------------------------------------------------------

RCM_PATH_OPTION = click.option(
    "--rcm",
    "rcm_path",
    required=False,
    default=None,
    envvar="JLESSON_RCM_PATH",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Path to the RCM directory (contains rcm.db). Defaults to JLESSON_RCM_PATH env var.",
)


@cli.group()
def rcm() -> None:
    """Query and inspect the RCM database."""


@rcm.command("items")
@RCM_PATH_OPTION
@click.option("--phase", default=None, type=click.Choice(["nouns", "verbs", "adjectives", "sentences"]), help="Filter by item phase.")
@click.option("--language", default=None, help="Filter to items that have a branch for this language code.")
@click.option("--min-branches", type=int, default=None, help="Only show items with at least this many branches.")
@click.option("--text", "text_filter", default=None, help="Case-insensitive substring filter on canonical text.")
@click.option("--limit", default=50, show_default=True, help="Maximum rows to display.")
def rcm_items(
    rcm_path: Path | None,
    phase: str | None,
    language: str | None,
    min_branches: int | None,
    text_filter: str | None,
    limit: int,
) -> None:
    """Query canonical items in the RCM store with optional filters.

    Examples:

    \b
      # Items with more than one branch (shared across languages or duplicates)
      jlesson rcm items --min-branches 2

      # French verbs containing 'arriver'
      jlesson rcm items --phase verbs --language eng-fre --text arriver

      # All sentences stored for English-Japanese
      jlesson rcm items --phase sentences --language eng-jap --limit 100
    """
    if rcm_path is None:
        raise click.UsageError("Specify --rcm or set JLESSON_RCM_PATH.")
    from sqlalchemy import text as sa_text
    from .rcm import open_rcm

    with open_rcm(rcm_path) as store:
        with store._Session() as session:
            # Build query joining items → branches
            where: list[str] = []
            params: dict = {}

            if phase:
                where.append("i.phase = :phase")
                params["phase"] = phase

            if text_filter:
                where.append("i.text_normalized LIKE :text")
                params["text"] = f"%{text_filter.lower()}%"

            if language:
                where.append(
                    "EXISTS (SELECT 1 FROM branches b2 WHERE b2.item_id = i.id AND b2.language_code = :lang)"
                )
                params["lang"] = language

            where_clause = ("WHERE " + " AND ".join(where)) if where else ""

            rows = session.execute(sa_text(f"""
                SELECT i.id, i.text, i.phase, COUNT(b.id) AS branch_count,
                       GROUP_CONCAT(b.language_code, ', ') AS languages
                FROM items i
                LEFT JOIN branches b ON b.item_id = i.id
                {where_clause}
                GROUP BY i.id
                HAVING (:min_b IS NULL OR branch_count >= :min_b)
                ORDER BY branch_count DESC, i.phase, i.text_normalized
                LIMIT :lim
            """), {**params, "min_b": min_branches, "lim": limit}).fetchall()

    if not rows:
        click.echo("No items match the given filters.")
        return

    click.echo(f"\n  {'ID':<36}  {'Phase':<12}  {'Br':>2}  {'Languages':<20}  Text")
    click.echo(f"  {'-'*36}  {'-'*12}  {'--':>2}  {'-'*20}  {'-'*40}")
    for item_id, text, item_phase, branch_count, languages in rows:
        langs_str = (languages or "").replace(", ", ",")
        click.echo(f"  {item_id:<36}  {(item_phase or ''):12}  {branch_count:>2}  {langs_str:<20}  {text}")

    click.echo(f"\n  {len(rows)} row(s) shown (limit={limit}).")


@rcm.command("stats")
@RCM_PATH_OPTION
def rcm_stats(rcm_path: Path | None) -> None:
    """Show a summary of all records in the RCM database."""
    if rcm_path is None:
        raise click.UsageError("Specify --rcm or set JLESSON_RCM_PATH.")
    from .rcm import open_rcm

    with open_rcm(rcm_path) as store:
        s = store.stats()

    click.echo(f"Items           : {s['items']}")
    click.echo(f"Branches        : {s['branches']}")
    click.echo(f"Assets          : {s['assets']}")
    click.echo(f"Lesson items    : {s['lesson_items']}")
    click.echo(f"LLM usage records: {s['llm_usage_records']}  (links: {s['llm_usage_links']})")
    click.echo(f"LLM tokens      : prompt={s['llm_prompt_tokens']}  completion={s['llm_completion_tokens']}  total={s['llm_total_tokens']}")
    if s["duplicate_texts"]:
        click.echo(f"\nDuplicate canonical texts ({len(s['duplicate_texts'])}):")
        for d in s["duplicate_texts"][:10]:
            click.echo(f"  '{d['text']}' × {d['count']}")
        if len(s["duplicate_texts"]) > 10:
            click.echo(f"  … and {len(s['duplicate_texts']) - 10} more")


@rcm.command("lessons")
@RCM_PATH_OPTION
def rcm_lessons(rcm_path: Path | None) -> None:
    """List all lessons and their item counts."""
    if rcm_path is None:
        raise click.UsageError("Specify --rcm or set JLESSON_RCM_PATH.")
    from sqlalchemy import text as sa_text
    from .rcm import open_rcm

    with open_rcm(rcm_path) as store:
        with store._Session() as session:
            rows = session.execute(sa_text(
                "SELECT lesson_id, language_code, theme, COUNT(*) as cnt "
                "FROM lesson_items GROUP BY lesson_id, language_code, theme "
                "ORDER BY lesson_id, theme"
            )).fetchall()

    if not rows:
        click.echo("No lessons found.")
        return

    click.echo(f"\n  {'ID':>4}  {'Language':<12}  {'Items':>5}  Theme")
    click.echo(f"  {'-'*4}  {'-'*12}  {'-'*5}  {'-'*50}")
    for row in rows:
        click.echo(f"  {row[0]:>4}  {row[1]:<12}  {row[3]:>5}  {row[2]}")


@rcm.command("lesson-assets")
@click.argument("lesson_id", type=int)
@LANGUAGE_OPTION
@RCM_PATH_OPTION
@click.option(
    "--fix",
    is_flag=True,
    default=False,
    help=(
        "Migrate legacy absolute-path entries to relative paths: copies each file "
        "into the RCM assets directory and re-registers it as assets/<filename>."
    ),
)
def rcm_lesson_assets(lesson_id: int, language: str, rcm_path: Path | None, fix: bool) -> None:
    """Check compiled asset availability for all items in LESSON_ID.

    Lists every registered asset entry, shows whether the stored path is
    relative (preferred) or absolute (legacy), and whether the file exists.

    With --fix, absolute-path entries whose files still exist are copied into
    the RCM assets directory and re-registered as relative paths.

    Example:
        jlesson rcm lesson-assets 3 --language eng-fre
        jlesson rcm lesson-assets 3 --language eng-fre --fix
    """
    if rcm_path is None:
        raise click.UsageError("Specify --rcm or set JLESSON_RCM_PATH.")
    from sqlalchemy import text as sa_text
    from .rcm import open_rcm

    with open_rcm(rcm_path) as store:
        with store._Session() as session:
            item_ids = [
                row[0] for row in session.execute(sa_text(
                    "SELECT item_id FROM lesson_items "
                    "WHERE lesson_id = :lid AND language_code = :lang "
                    "ORDER BY item_id"
                ), {"lid": lesson_id, "lang": language}).fetchall()
            ]

        if not item_ids:
            with store._Session() as session:
                available = [
                    row[0] for row in session.execute(sa_text(
                        "SELECT DISTINCT language_code FROM lesson_items WHERE lesson_id = :lid"
                    ), {"lid": lesson_id}).fetchall()
                ]
            if available:
                hint = f"  Available languages: {', '.join(sorted(available))}"
                raise click.UsageError(
                    f"No items found for lesson {lesson_id} with language '{language}'.\n{hint}"
                )
            raise click.UsageError(f"Lesson {lesson_id} not found in the RCM store.")

        # Collect all asset rows for these items in one query
        placeholders = ",".join(f"'{i}'" for i in item_ids)
        with store._Session() as session:
            asset_rows = session.execute(sa_text(
                f"SELECT item_id, asset_key, file_path FROM assets "
                f"WHERE item_id IN ({placeholders}) AND language_code = :lang "
                f"ORDER BY item_id, asset_key"
            ), {"lang": language}).fetchall()

        total = missing = n_absolute = fixed = 0

        click.echo(f"\nLesson {lesson_id}  [{language}]  —  {len(item_ids)} item(s)\n")
        click.echo(f"  {'Item ID':<36}  {'Key':<20}  {'OK':>2}  {'Path type':>9}  Stored path")
        click.echo(f"  {'-'*36}  {'-'*20}  {'--':>2}  {'-'*9}  {'-'*55}")

        to_fix: list[tuple[str, str, Path]] = []  # (item_id, asset_key, resolved_path)

        for item_id, asset_key, stored_path in asset_rows:
            total += 1
            is_relative = not Path(stored_path).is_absolute()
            resolved = (
                store._store_root / stored_path
                if is_relative
                else Path(stored_path)
            )
            exists = resolved.exists()
            if not exists:
                missing += 1
            if not is_relative:
                n_absolute += 1
                if fix and exists:
                    to_fix.append((item_id, asset_key, resolved))

            ok_mark = "✓" if exists else "✗"
            path_type = "relative" if is_relative else "absolute"
            click.echo(
                f"  {item_id:<36}  {asset_key:<20}  {ok_mark:>2}  {path_type:>9}  {stored_path}"
            )

        # Run fixes (outside the session loop)
        for item_id, asset_key, resolved in to_fix:
            store.register_asset(item_id, language, asset_key, resolved, copy_to_store=True)
            fixed += 1

        click.echo(f"\n  Items in lesson  : {len(item_ids)}")
        click.echo(f"  Asset records    : {total}")
        click.echo(f"  Missing on disk  : {missing}")
        click.echo(f"  Absolute paths   : {n_absolute}")
        if fix:
            click.echo(f"  Fixed (migrated) : {fixed}")
        elif n_absolute:
            click.echo(f"  Run with --fix to migrate absolute paths to relative.")


@rcm.command("lesson-usage")
@click.argument("lesson_id", type=int)
@LANGUAGE_OPTION
@RCM_PATH_OPTION
@click.option("--verbose", "-v", is_flag=True, default=False, help="Show per-call LLM records.")
def rcm_lesson_usage(lesson_id: int, language: str, rcm_path: Path, verbose: bool) -> None:
    """Show items and LLM usage for LESSON_ID.

    Example:
        jlesson rcm lesson-usage 3 --rcm ~/.jlesson/northern_exposure --language eng-jap
    """
    from .rcm import open_rcm

    with open_rcm(rcm_path) as store:
        report = store.lesson_usage_report(lesson_id, language_code=language)

    items = report["items"]
    totals = report["totals"]

    if not items:
        from sqlalchemy import text as sa_text
        with open_rcm(rcm_path) as store:
            with store._Session() as session:
                available = [
                    row[0] for row in session.execute(sa_text(
                        "SELECT DISTINCT language_code FROM lesson_items WHERE lesson_id = :lid"
                    ), {"lid": lesson_id}).fetchall()
                ]
        if available:
            hint = f"  Available languages: {', '.join(sorted(available))}"
            raise click.UsageError(
                f"No items found for lesson {lesson_id} with language '{language}'.\n{hint}"
            )
        raise click.UsageError(f"Lesson {lesson_id} not found in the RCM store.")

    click.echo(f"\nLesson {lesson_id}  [{language}]  —  {len(items)} item(s)\n")
    click.echo(f"  {'Item ID':<36}  {'Text':<30}  {'Phase':<10}  {'Theme':<18}  Calls  Tokens")
    click.echo(f"  {'-'*36}  {'-'*30}  {'-'*10}  {'-'*18}  -----  ------")

    for item in items:
        u = item["llm_usage"]
        click.echo(
            f"  {item['item_id']:<36}  {item['text']:<30}  {item['phase']:<10}"
            f"  {item['theme']:<18}  {u['records']:>5}  {u['total_tokens']:>6}"
        )
        if verbose and item["llm_records"]:
            for rec in item["llm_records"]:
                hit = "HIT " if rec["cache_hit"] else "MISS"
                click.echo(
                    f"      [{hit}] {rec['step_name'] or '(unknown)':25}"
                    f"  rel={rec['relation_type']:<10}"
                    f"  p={rec['prompt_tokens']:>5}  c={rec['completion_tokens']:>5}"
                    f"  total={rec['total_tokens']:>6}"
                )

    click.echo(f"  {'-'*36}  {'-'*30}  {'-'*10}  {'-'*18}  -----  ------")
    click.echo(
        f"  {'TOTAL':<36}  {'':30}  {'':10}  {'':18}  {totals['records']:>5}  {totals['total_tokens']:>6}"
    )
    click.echo(
        f"\n  Prompt tokens: {totals['prompt_tokens']}  "
        f"Completion tokens: {totals['completion_tokens']}  "
        f"Total tokens: {totals['total_tokens']}"
    )


@rcm.command("item-usage")
@click.argument("item_id")
@LANGUAGE_OPTION
@RCM_PATH_OPTION
@click.option("--verbose", "-v", is_flag=True, default=False, help="Show per-call LLM records.")
def rcm_item_usage(item_id: str, language: str, rcm_path: Path, verbose: bool) -> None:
    """Show LLM usage for a single canonical item ITEM_ID.

    Example:
        jlesson rcm item-usage abc123def456 --rcm ~/.jlesson/northern_exposure
    """
    from .rcm import open_rcm

    with open_rcm(rcm_path) as store:
        report = store.item_usage_report(item_id, language_code=language)

    if "error" in report:
        click.echo(f"Item '{item_id}' not found in the RCM database.", err=True)
        raise SystemExit(1)

    u = report["llm_usage"]
    click.echo(f"\nItem: {report['text']}  ({report['item_id']})")
    click.echo(f"Phase: {report['phase']}   Language: {language}")
    click.echo(f"LLM calls: {u['records']}  —  "
               f"prompt: {u['prompt_tokens']}  completion: {u['completion_tokens']}  total: {u['total_tokens']}")

    if verbose and report["llm_records"]:
        click.echo()
        for rec in report["llm_records"]:
            hit = "HIT " if rec["cache_hit"] else "MISS"
            click.echo(
                f"  [{hit}] {rec['step_name'] or '(unknown)':25}"
                f"  rel={rec['relation_type']:<10}"
                f"  p={rec['prompt_tokens']:>5}  c={rec['completion_tokens']:>5}"
                f"  total={rec['total_tokens']:>6}"
            )


# ---------------------------------------------------------------------------
# rcm vector-status
# ---------------------------------------------------------------------------

@rcm.command("vector-status")
@RCM_PATH_OPTION
@click.option("--phase", default=None,
              type=click.Choice(["nouns", "verbs", "adjectives", "vocab", "grammar", "narrative"]),
              help="Filter by item phase.")
@click.option("--list-missing", is_flag=True, default=False,
              help="Print IDs and texts of SQL items not yet indexed in the vector DB.")
def rcm_vector_status(
    rcm_path: Path | None,
    phase: str | None,
    list_missing: bool,
) -> None:
    """Compare SQL canonical items against the Chroma vector index.

    The Chroma DB is always located at <rcm>/chroma (same directory as rcm.db).
    Use --rcm or JLESSON_RCM_PATH to point at the RCM directory.

    Examples:

    \b
      # Overall summary
      jlesson rcm vector-status

      # Nouns only, show what needs to be added
      jlesson rcm vector-status --phase nouns --list-missing
    """
    if rcm_path is None:
        raise click.UsageError("Specify --rcm or set JLESSON_RCM_PATH.")

    from sqlalchemy import text as sa_text
    from .rcm import open_rcm

    resolved_chroma = rcm_path / "chroma"

    # --- Load SQL items ---
    with open_rcm(rcm_path) as store:
        with store._Session() as session:
            where = "WHERE i.phase = :phase" if phase else ""
            params: dict = {"phase": phase} if phase else {}
            sql_rows = session.execute(sa_text(f"""
                SELECT i.id, i.text, i.phase
                FROM items i
                {where}
                ORDER BY i.phase, i.text_normalized
            """), params).fetchall()

    sql_ids: dict[str, tuple[str, str]] = {row[0]: (row[1], row[2]) for row in sql_rows}

    # --- Load Chroma IDs ---
    chroma_ids: set[str] = set()
    chroma_total: int = 0
    chroma_available = False
    chroma_error: str = ""

    if resolved_chroma.exists():
        try:
            import chromadb
            from .rcm.retrieval import RCMVectorRetrievalService
            client = chromadb.PersistentClient(path=str(resolved_chroma))
            try:
                collection = client.get_collection(RCMVectorRetrievalService.COLLECTION_NAME)
                chroma_total = collection.count()
                # Fetch all IDs without embeddings (cheap)
                if chroma_total > 0:
                    result = collection.get(include=[])
                    chroma_ids = set(result.get("ids", []))
                chroma_available = True
            except Exception:
                chroma_error = "collection not found — no items ingested yet"
                chroma_available = True
        except ImportError:
            chroma_error = "chromadb is not installed"
    else:
        chroma_error = f"Chroma path does not exist: {resolved_chroma}"

    # --- Compute diff ---
    in_sql = len(sql_ids)
    in_chroma = len(chroma_ids & sql_ids.keys())
    missing_ids = {k: v for k, v in sql_ids.items() if k not in chroma_ids}
    extra_ids = chroma_ids - sql_ids.keys()   # in Chroma but not in SQL (stale)

    # --- Report ---
    filter_label = f" (phase={phase})" if phase else ""
    click.echo(f"\nRCM Vector Status{filter_label}")
    click.echo(f"  RCM path   : {rcm_path}")
    click.echo(f"  Chroma path: {resolved_chroma}")

    if chroma_error:
        click.echo(f"\n  Chroma     : {chroma_error}")
    else:
        click.echo(f"\n  SQL items        : {in_sql}")
        click.echo(f"  Chroma indexed   : {in_chroma}")
        click.echo(f"  Missing (SQL→Vec): {len(missing_ids)}")
        if extra_ids:
            click.echo(f"  Stale  (Vec→SQL) : {len(extra_ids)}  (in Chroma but no longer in SQL)")

    if list_missing and missing_ids:
        click.echo(f"\n  Items not yet indexed ({len(missing_ids)}):")
        click.echo(f"  {'ID':<36}  {'Phase':<12}  Text")
        click.echo(f"  {'-'*36}  {'-'*12}  {'-'*40}")
        for item_id, (text, item_phase) in sorted(missing_ids.items(), key=lambda x: (x[1][1], x[1][0])):
            click.echo(f"  {item_id:<36}  {item_phase:<12}  {text}")
    elif list_missing and not missing_ids:
        click.echo("\n  All SQL items are indexed in the vector DB.")

    click.echo()


@rcm.command("vector-sync")
@RCM_PATH_OPTION
@click.option("--phase", default=None,
              type=click.Choice(["nouns", "verbs", "adjectives", "vocab", "grammar", "narrative"]),
              help="Sync only items of this phase.")
@click.option("--embedding-model", default="text-embedding-3-small", show_default=True,
              help="Embedding model to use for items that need a new embedding.")
@click.option("--dry-run", is_flag=True, default=False,
              help="Show what would be synced without making any changes.")
def rcm_vector_sync(
    rcm_path: Path | None,
    phase: str | None,
    embedding_model: str,
    dry_run: bool,
) -> None:
    """Sync SQL canonical items into the Chroma vector index.

    Only items not yet present in Chroma are processed.  Items whose
    embeddings are already stored in SQL are reused (no API call);
    only genuinely new items require an embedding model call.

    Examples:

    \b
      # Sync everything
      jlesson rcm vector-sync

      # Preview without writing
      jlesson rcm vector-sync --dry-run

      # Sync nouns only
      jlesson rcm vector-sync --phase nouns
    """
    if rcm_path is None:
        raise click.UsageError("Specify --rcm or set JLESSON_RCM_PATH.")

    from sqlalchemy import text as sa_text
    from .rcm import open_rcm, RCMVectorRetrievalService

    resolved_chroma = rcm_path / "chroma"

    with open_rcm(rcm_path) as store:
        # Fetch SQL items
        with store._Session() as session:
            where = "WHERE phase = :phase" if phase else ""
            params: dict = {"phase": phase} if phase else {}
            sql_rows = session.execute(sa_text(f"""
                SELECT id FROM items {where} ORDER BY phase, text_normalized
            """), params).fetchall()

        sql_ids: list[str] = [row[0] for row in sql_rows]

        # Determine which are already in Chroma
        chroma_ids: set[str] = set()
        try:
            import chromadb
            if resolved_chroma.exists():
                client = chromadb.PersistentClient(path=str(resolved_chroma))
                try:
                    collection = client.get_collection(RCMVectorRetrievalService.COLLECTION_NAME)
                    if collection.count() > 0:
                        result = collection.get(include=[])
                        chroma_ids = set(result.get("ids", []))
                except Exception:
                    pass  # collection doesn't exist yet — all items are missing
        except ImportError:
            click.echo("Error: chromadb is not installed. Run: pip install chromadb", err=True)
            raise SystemExit(1)

        missing = [item_id for item_id in sql_ids if item_id not in chroma_ids]
        filter_label = f" (phase={phase})" if phase else ""
        click.echo(f"\nRCM Vector Sync{filter_label}")
        click.echo(f"  SQL items   : {len(sql_ids)}")
        click.echo(f"  Already indexed: {len(sql_ids) - len(missing)}")
        click.echo(f"  To index    : {len(missing)}")

        if not missing:
            click.echo("\n  Nothing to sync.")
            click.echo()
            return

        if dry_run:
            click.echo(f"\n  Dry run — would ingest {len(missing)} item(s):")
            for item_id in missing:
                item = store.get_item(item_id)
                cached = " (embedding cached)" if item and item.embeddings else ""
                click.echo(f"    {item_id}  {item.text if item else '?'}{cached}")
            click.echo()
            return

        # Ingest missing items
        items_to_sync = [store.get_item(item_id) for item_id in missing]
        items_to_sync = [it for it in items_to_sync if it is not None]

        svc = RCMVectorRetrievalService(store, resolved_chroma, embedding_model=embedding_model)

        with click.progressbar(length=len(items_to_sync), label="  Indexing", show_pos=True) as bar:
            def _progress(n_done: int, _n_total: int) -> None:
                bar.update(n_done - bar.pos)

            n_cached, n_generated = svc.ingest_items_batch(items_to_sync, progress_callback=_progress)

        click.echo(f"\n  Done.  Indexed {len(items_to_sync)} item(s).")
        click.echo(f"  Embeddings reused from SQL : {n_cached}")
        click.echo(f"  Embeddings generated (API) : {n_generated}")
        click.echo()


@rcm.command("vector-search")
@RCM_PATH_OPTION
@click.argument("query")
@click.option("--language", default=None,
              help="Narrow results to items that have a branch for this language code (e.g. hun-ger).")
@click.option("--phase", default=None,
              type=click.Choice(["nouns", "verbs", "adjectives", "vocab", "grammar", "narrative"]),
              help="Filter by item phase.")
@click.option("--limit", default=10, show_default=True, help="Number of results to return.")
@click.option("--embedding-model", default="text-embedding-3-small", show_default=True,
              help="Embedding model used to encode the query.")
def rcm_vector_search(
    rcm_path: Path | None,
    query: str,
    language: str | None,
    phase: str | None,
    limit: int,
    embedding_model: str,
) -> None:
    """Semantic vector search over canonical items.

    QUERY is a free-text English phrase. Results are canonical items ranked
    by similarity. Use --language to narrow to items that also have a branch
    for a specific language.

    Examples:

    \b
      # Find nouns related to farm animals with a German branch
      jlesson rcm vector-search "farm animals" --language hun-ger --phase nouns

      # Find grammar sentences about past tense
      jlesson rcm vector-search "past tense action" --phase grammar --limit 5

      # Canonical search only, no language filter
      jlesson rcm vector-search "daily routine verbs"
    """
    if rcm_path is None:
        raise click.UsageError("Specify --rcm or set JLESSON_RCM_PATH.")

    from .models import Phase as PhaseEnum
    from .rcm import open_rcm, RCMVectorRetrievalService

    resolved_chroma = rcm_path / "chroma"

    if not resolved_chroma.exists():
        click.echo("Vector index not found. Run: jlesson rcm vector-sync", err=True)
        raise SystemExit(1)

    phase_enum = PhaseEnum(phase) if phase else None

    with open_rcm(rcm_path) as store:
        svc = RCMVectorRetrievalService(store, resolved_chroma, embedding_model=embedding_model)

        if language:
            results = svc.search(query, language, phase=phase_enum, limit=limit)
            click.echo(f"\nVector search: '{query}'  language={language}" + (f"  phase={phase}" if phase else ""))
            click.echo(f"  {'Score':<7}  {'Phase':<12}  {'Canonical':<35}  Target")
            click.echo(f"  {'-'*7}  {'-'*12}  {'-'*35}  {'-'*35}")
            if not results:
                click.echo("  No results.")
            for canonical, branch in results:
                target_text = branch.target.display_text if branch.target else ""
                click.echo(
                    f"           "
                    f"  {(canonical.type.value if canonical.type else ''):12}"
                    f"  {canonical.text:<35}"
                    f"  {target_text}"
                )
        else:
            # No language filter — search canonical only via Chroma directly
            try:
                import chromadb
            except ImportError:
                click.echo("chromadb is not installed.", err=True)
                raise SystemExit(1)

            query_embedding = svc._embed_texts([query])[0]
            client = chromadb.PersistentClient(path=str(resolved_chroma))
            collection = client.get_collection(RCMVectorRetrievalService.COLLECTION_NAME)

            kwargs: dict = {
                "query_embeddings": [query_embedding],
                "n_results": limit,
                "include": ["distances", "documents", "metadatas"],
            }
            if phase:
                kwargs["where"] = {"phase": phase}

            result = collection.query(**kwargs)
            ids = result.get("ids") or [[]]
            ids = ids[0]
            distances = (result.get("distances") or [[]])[0]
            metadatas = (result.get("metadatas") or [[]])[0]

            click.echo(f"\nVector search: '{query}'" + (f"  phase={phase}" if phase else ""))
            click.echo(f"  {'Score':<7}  {'Phase':<12}  {'ID':<36}  Text")
            click.echo(f"  {'-'*7}  {'-'*12}  {'-'*36}  {'-'*35}")
            if not ids:
                click.echo("  No results.")
            for i, item_id in enumerate(ids):
                dist = distances[i] if i < len(distances) else 0.0
                score = 1.0 / (1.0 + dist)
                meta = metadatas[i] if i < len(metadatas) else {}
                item = store.get_item(item_id)
                text = item.text if item else item_id
                click.echo(
                    f"  {score:.4f}  "
                    f"  {meta.get('phase', ''):12}"
                    f"  {item_id:<36}"
                    f"  {text}"
                )

    click.echo()


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
