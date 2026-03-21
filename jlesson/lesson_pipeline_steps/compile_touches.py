from __future__ import annotations

import jlesson.touch_compiler as touch_compiler
from jlesson.profiles import get_profile

from .runtime import lesson_pipeline_module


class CompileTouchesStep(lesson_pipeline_module().PipelineStep):
    """Step 10 — Profile-driven touch sequencing (Stage 3)."""

    name = "compile_touches"
    description = "Profile-driven touch sequencing"

    def execute(self, ctx: lesson_pipeline_module().LessonContext) -> lesson_pipeline_module().LessonContext:
        profile = get_profile(ctx.config.profile)
        ctx.touches = touch_compiler.compile_touches(ctx.compiled_items, profile)
        self._log(
            ctx,
            f"       {len(ctx.touches)} touches "
            f"(profile: {ctx.config.profile})",
        )
        return ctx