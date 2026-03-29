from __future__ import annotations

import time
from jlesson.language_config import get_language_config
from jlesson.pipeline_steps.pipeline_core import LessonConfig, LessonContext, PipelineStep, StepInfo


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
        ctx.report.record_time(step.name, time.time() - t_step)

    elapsed = time.time() - t_total
    print(f"\n  Done - {elapsed:.0f}s")
    if ctx.video_path and ctx.video_path.exists():
        print(f"  Video   : {ctx.video_path}")
    if ctx.content_path:
        print(f"  Content : {ctx.content_path}")
    if ctx.report_path:
        print(f"  Report  : {ctx.report_path}")
    return ctx