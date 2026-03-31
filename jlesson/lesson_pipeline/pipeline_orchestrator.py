from __future__ import annotations

import time
from pathlib import Path
from jlesson.language_config import get_language_config
from jlesson.pipeline_steps.pipeline_core import LessonConfig, LessonContext, PipelineStep, StepInfo


def _resolve_checkpoint_path(ctx: LessonContext) -> Path:
    """Return the path to write the checkpoint to.

    Uses ``ctx.content_path`` when the lesson has been registered (or the ID
    was known upfront).  Falls back to a ``lesson_pending/`` directory inside
    the language+theme output folder for the early steps of ``lesson add``
    before registration.
    """
    if ctx.content_path is not None:
        return ctx.content_path
    from jlesson.lesson_pipeline.pipeline_paths import resolve_lang_dir
    pending_dir = resolve_lang_dir(ctx.config) / ctx.config.theme / "lesson_pending"
    return pending_dir / "content.json"


def _save_context_checkpoint(ctx: LessonContext) -> None:
    """Overwrite content.json with the current lesson context snapshot.

    Called after every step.  Includes completed steps and their timings so
    the JSON file always reflects the latest pipeline state.
    """
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
        completed_steps=list(ctx.completed_steps),
        step_timings=dict(ctx.step_timings),
    )
    save_lesson_content(content, checkpoint_path.parent)


def run_pipeline(
    config: LessonConfig,
    *,
    pipeline: list[PipelineStep],
    load_curriculum_fn,
) -> LessonContext:
    """Run the full lesson generation pipeline."""
    from jlesson.lesson_pipeline.pipeline_paths import resolve_lesson_dir

    ctx = LessonContext(config=config)
    ctx.language_config = get_language_config(config.language)
    ctx.curriculum = load_curriculum_fn(config.curriculum_path)

    # Pre-resolve content_path when the lesson ID is already known (lesson update).
    # This enables checkpointing into the real lesson dir from step 1.
    if config.regenerate_lesson_id is not None:
        ctx.lesson_id = config.regenerate_lesson_id
        ctx.content_path = resolve_lesson_dir(config, config.regenerate_lesson_id) / "content.json"

    total = len(pipeline)

    print(f"\n{'=' * 60}")
    print(f"  LESSON: {config.theme.upper()}")
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
        t_step = time.time()
        ctx = step.execute(ctx)
        step_elapsed = time.time() - t_step
        ctx.report.record_time(step.name, step_elapsed)
        ctx.completed_steps.append(step.name)
        ctx.step_timings[step.name] = round(step_elapsed, 3)
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