from __future__ import annotations

import jlesson.touch_compiler as touch_compiler
from .pipeline_core import LessonContext, PipelineStep
from jlesson.profiles import get_profile


class CompileTouchesStep(PipelineStep):
    """Step 10 — Profile-driven touch sequencing (Stage 3)."""

    name = "compile_touches"
    description = "Profile-driven touch sequencing"

    def execute(self, ctx: LessonContext) -> LessonContext:
        profile = get_profile(ctx.config.profile)
        ctx.touches = touch_compiler.compile_touches(ctx.compiled_items, profile)
        self._log(
            ctx,
            f"       {len(ctx.touches)} touches "
            f"across {ctx.config.lesson_blocks} blocks (profile: {ctx.config.profile})",
        )
        return ctx