from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

from jlesson.language_config import get_language_config
from jlesson.pipeline_steps.pipeline_core import LessonConfig, LessonContext, PipelineStep, StepInfo

# ---------------------------------------------------------------------------
# JSON serialisation helpers (Path-safe, non-raising)
# ---------------------------------------------------------------------------

def _to_json_safe(obj):
    """Recursively convert obj into a JSON-serialisable value."""
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, dict):
        return {k: _to_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_json_safe(i) for i in obj]
    if hasattr(obj, "model_dump"):
        try:
            return obj.model_dump(mode="json")
        except Exception:
            return repr(obj)
    try:
        from dataclasses import asdict, is_dataclass
        if is_dataclass(obj) and not isinstance(obj, type):
            return _to_json_safe(asdict(obj))
    except Exception:
        pass
    try:
        json.dumps(obj)
        return obj
    except (TypeError, ValueError):
        return repr(obj)


# ---------------------------------------------------------------------------
# Step artifact helpers
# ---------------------------------------------------------------------------

def _step_artifact_dir(ctx: LessonContext, step_name: str) -> Path | None:
    """Return ``lesson_dir/steps/<step_name>`` or None when lesson_id unknown."""
    if ctx.lesson_id <= 0:
        return None
    from jlesson.lesson_pipeline.pipeline_paths import resolve_lesson_dir
    return resolve_lesson_dir(ctx.config, ctx.lesson_id) / "steps" / step_name


def _save_step_artifacts(ctx: LessonContext, step_name: str, chunks, outputs) -> None:
    """Write ``steps/<step_name>/input.json`` and ``output.json``."""
    artifact_dir = _step_artifact_dir(ctx, step_name)
    if artifact_dir is None:
        return
    try:
        artifact_dir.mkdir(parents=True, exist_ok=True)
        if chunks:
            (artifact_dir / "input.json").write_text(
                json.dumps(_to_json_safe(chunks), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        if outputs:
            (artifact_dir / "output.json").write_text(
                json.dumps(_to_json_safe(outputs), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
    except Exception:
        pass  # artifact writing is best-effort; never break the pipeline


# ---------------------------------------------------------------------------
# Checkpoint helpers
# ---------------------------------------------------------------------------

def _resolve_checkpoint_path(ctx: LessonContext) -> Path:
    """Return the path to write the checkpoint to."""
    if ctx.content_path is not None:
        return ctx.content_path
    from jlesson.lesson_pipeline.pipeline_paths import resolve_lang_dir
    pending_dir = resolve_lang_dir(ctx.config) / ctx.config.theme / "lesson_pending"
    return pending_dir / "content.json"


def _save_context_checkpoint(ctx: LessonContext) -> None:
    """Overwrite content.json with the current lesson context snapshot."""
    from jlesson.lesson_store import save_lesson_content
    from jlesson.models import LessonContent

    checkpoint_path = _resolve_checkpoint_path(ctx)
    content = LessonContent(
        lesson_id=ctx.lesson_id,
        theme=ctx.config.theme,
        language=ctx.config.language,
        narrative_blocks=ctx.narrative_blocks,
        grammar_ids=[g.id for g in ctx.selected_grammar],
        words=[*ctx.noun_items, *ctx.verb_items],
        sentences=ctx.sentences,
        created_at=ctx.created_at,
        pipeline_started_at=ctx.pipeline_started_at,
        completed_steps=list(ctx.completed_steps),
        step_timings=dict(ctx.step_timings),
        step_details=dict(ctx.step_details),
    )
    save_lesson_content(content, checkpoint_path.parent)


# ---------------------------------------------------------------------------
# Context restoration from checkpoint
# ---------------------------------------------------------------------------

def _wire_assets_from_disk(ctx: LessonContext) -> LessonContext:
    """Attach on-disk asset paths to items, then populate ctx.compiled_items."""
    from jlesson.models import CompiledItem, Phase
    from jlesson.pipeline_steps.pipeline_core import LessonContext
    from jlesson.lesson_pipeline.pipeline_paths import resolve_lesson_dir
    from jlesson.profiles import get_profile

    lesson_dir = resolve_lesson_dir(ctx.config, ctx.lesson_id)
    cards_dir = lesson_dir / "cards"
    audio_dir = lesson_dir / "audio"

    profile_obj = get_profile(ctx.config.profile)

    _card_suffix = {
        "card_src": "src",
        "card_tar": "tar",
        "card_src_tar": "src_tar",
    }

    items_by_phase = {
        Phase.NOUNS: ctx.noun_items,
        Phase.VERBS: ctx.verb_items,
        Phase.GRAMMAR: ctx.sentences,
    }

    compiled: list[CompiledItem] = []
    item_index = 0
    for phase in (Phase.NOUNS, Phase.VERBS, Phase.GRAMMAR):
        items = items_by_phase.get(phase, [])
        required = profile_obj.required_assets(phase)
        for item in items:
            item_index += 1
            for asset_key in required:
                if asset_key.startswith("card_"):
                    suffix = _card_suffix.get(asset_key)
                    if suffix:
                        path = cards_dir / f"{item_index:03d}_{suffix}.png"
                        if path.exists():
                            if "src" in asset_key and asset_key != "card_src_tar":
                                item.source.assets[asset_key] = path
                            else:
                                item.target.assets[asset_key] = path
                elif asset_key.startswith("audio_"):
                    path = audio_dir / f"{item_index:03d}_{asset_key}.mp3"
                    if path.exists():
                        if asset_key == "audio_src":
                            item.source.assets[asset_key] = path
                        else:
                            item.target.assets[asset_key] = path
            compiled_item = CompiledItem(**item.model_dump())
            compiled_item.phase = phase
            compiled.append(compiled_item)

    ctx.compiled_items = compiled
    return ctx


def restore_context_from_checkpoint(
    config: LessonConfig,
    *,
    load_curriculum_fn,
    wire_assets: bool = True,
) -> LessonContext:
    """Load a saved lesson checkpoint and restore a renderable LessonContext.

    Sets ctx fields so that all LLM-generating steps naturally skip via their
    ``should_skip`` guards, and only the render sub-pipeline executes.

    Args:
        config: LessonConfig with ``regenerate_lesson_id`` set.
        load_curriculum_fn: callable returning ``CurriculumData``.
        wire_assets: when True, resolve existing asset files from disk into
            ``ctx.compiled_items`` (so ``compile_assets`` skips).  Pass
            ``False`` to force full asset recompilation from ``--from-step
            compile_assets``.
    """
    from jlesson.lesson_store import load_lesson_content
    from jlesson.lesson_pipeline.pipeline_paths import resolve_lesson_dir
    from jlesson.models import Phase

    lesson_id = config.regenerate_lesson_id
    if lesson_id is None:
        raise ValueError("restore_context_from_checkpoint requires regenerate_lesson_id")

    lesson_dir = resolve_lesson_dir(config, lesson_id)
    content = load_lesson_content(lesson_id, lesson_dir)

    ctx = LessonContext(config=config)
    ctx.language_config = get_language_config(config.language)
    ctx.curriculum = load_curriculum_fn(config.curriculum_path)

    # --- Restore content fields ---
    ctx.lesson_id = content.lesson_id
    ctx.created_at = content.created_at
    ctx.pipeline_started_at = content.pipeline_started_at
    ctx.narrative_blocks = list(content.narrative_blocks)
    ctx.noun_items = [i for i in content.words if i.phase == Phase.NOUNS]
    ctx.verb_items = [i for i in content.words if i.phase == Phase.VERBS]
    ctx.sentences = list(content.sentences)
    ctx.completed_steps = list(content.completed_steps)
    ctx.step_timings = dict(content.step_timings)
    ctx.step_details = dict(content.step_details)
    ctx.content_path = lesson_dir / "content.json"

    # Restore selected_grammar so grammar_ids round-trip
    from jlesson.models import GrammarItem
    ctx.selected_grammar = [
        GrammarItem(id=gid, pattern="", description="", example_source="", example_target="")
        for gid in content.grammar_ids
    ]

    # Dummy lesson_outline so lesson_planner skips
    from jlesson.pipeline_steps.pipeline_core import LessonOutline
    ctx.lesson_outline = LessonOutline(blocks=[], grammar_ids=content.grammar_ids)

    if wire_assets:
        ctx = _wire_assets_from_disk(ctx)

    return ctx


# ---------------------------------------------------------------------------
# Main pipeline runner
# ---------------------------------------------------------------------------

def run_pipeline(
    config: LessonConfig,
    *,
    pipeline: list[PipelineStep],
    load_curriculum_fn,
) -> LessonContext:
    """Run the lesson generation pipeline.

    When ``config.from_step`` is set, load the existing checkpoint and run only
    the render sub-pipeline (compile_assets → compile_touches → render_video →
    save_report), skipping all LLM-generation steps.
    """
    from jlesson.lesson_pipeline.pipeline_paths import resolve_lesson_dir

    if config.from_step is not None:
        # Determine whether to wire existing assets or recompile them
        wire_assets = config.from_step != "compile_assets"
        ctx = restore_context_from_checkpoint(
            config,
            load_curriculum_fn=load_curriculum_fn,
            wire_assets=wire_assets,
        )
        # Trim pipeline to the render sub-pipeline only
        _render_steps = {"compile_assets", "compile_touches", "render_video", "save_report"}
        pipeline = [s for s in pipeline if s.name in _render_steps]
    else:
        ctx = LessonContext(config=config)
        ctx.language_config = get_language_config(config.language)
        ctx.curriculum = load_curriculum_fn(config.curriculum_path)

        if config.regenerate_lesson_id is not None:
            ctx.lesson_id = config.regenerate_lesson_id
            ctx.content_path = (
                resolve_lesson_dir(config, config.regenerate_lesson_id) / "content.json"
            )

    # Stamp pipeline start time (preserve existing if restoring from checkpoint)
    if not ctx.pipeline_started_at:
        ctx.pipeline_started_at = (
            datetime.now(timezone.utc)
            .isoformat(timespec="seconds")
            .replace("+00:00", "Z")
        )

    total = len(pipeline)

    print(f"\n{'=' * 60}")
    print(f"  LESSON: {config.theme.upper()}")
    if config.from_step:
        print(f"  RESUME : from {config.from_step}")
    print(f"{'=' * 60}")

    t_total = time.time()
    for index, step in enumerate(pipeline, 1):
        info = StepInfo(
            index=index,
            total=total,
            name=step.name,
            description=step.description,
        )
        ctx.step_info = info
        if config.verbose:
            print(f"\n  {info.label} {step.description}")

        step_started_at = (
            datetime.now(timezone.utc)
            .isoformat(timespec="seconds")
            .replace("+00:00", "Z")
        )
        t_step = time.time()

        # Capture chunks before execution for artifact saving
        _chunks: list = []
        _outputs: list = []

        # Wrap ActionStep execution to capture chunks/outputs
        from jlesson.pipeline_steps.pipeline_core import ActionStep
        if isinstance(step, ActionStep) and not step.should_skip(ctx):
            _chunks = step.build_chunks(ctx)

        ctx = step.execute(ctx)

        step_elapsed = time.time() - t_step
        ctx.report.record_time(step.name, step_elapsed)
        ctx.completed_steps.append(step.name)
        ctx.step_timings[step.name] = round(step_elapsed, 3)
        ctx.step_details[step.name] = {
            "index": index,
            "description": step.description,
            "started_at": step_started_at,
            "elapsed_s": round(step_elapsed, 3),
            "status": "completed",
        }

        _save_step_artifacts(ctx, step.name, _chunks, _outputs)
        _save_context_checkpoint(ctx)

    elapsed = time.time() - t_total
    print(f"\n  Done - {elapsed:.0f}s")
    if ctx.video_path and ctx.video_path.exists():
        print(f"  Video   : {ctx.video_path}")
    if ctx.content_path:
        print(f"  Content : {ctx.content_path}")
    if ctx.report_path:
        print(f"  Report  : {ctx.report_path}")
    return ctx
