from __future__ import annotations

import time
from jlesson.language_config import get_language_config
from jlesson.pipeline_steps.pipeline_core import LessonConfig, LessonContext, PipelineStep, StepInfo


def _save_context_checkpoint(ctx: LessonContext) -> None:
    """Overwrite content.json with the current lesson context snapshot.

    Called after every step once the lesson has been registered and a
    content_path is known.  Includes completed steps and their timings so
    the JSON file always reflects the latest pipeline state.
    """
    from jlesson.lesson_store import save_lesson_content
    from jlesson.models import LessonContent

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
    save_lesson_content(content, ctx.content_path.parent)


def run_pipeline(
    config: LessonConfig,
    *,
    pipeline: list[PipelineStep],
    load_curriculum_fn,
) -> LessonContext:
    """Run the full lesson generation pipeline."""
    ctx = LessonContext(config=config)
    ctx.language_config = get_language_config(config.language)
    ctx.curriculum = load_curriculum_fn(config.curriculum_path)
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
        if ctx.content_path is not None:
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