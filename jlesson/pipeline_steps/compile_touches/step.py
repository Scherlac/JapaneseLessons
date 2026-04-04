from __future__ import annotations

from .action import CompileTouchesAction
from ..pipeline_core import ActionStep, GeneralItemSequence, LessonContext, TouchSequence


class CompileTouchesStep(ActionStep[GeneralItemSequence, TouchSequence]):
    """Step 10 — Profile-driven touch sequencing (Stage 3)."""

    name = "compile_touches"
    description = "Profile-driven touch sequencing"
    _action = CompileTouchesAction()

    @property
    def action(self) -> CompileTouchesAction:
        return self._action

    def should_skip(self, ctx: LessonContext) -> bool:
        return bool(ctx.touches)

    def build_chunks(self, ctx: LessonContext) -> list[GeneralItemSequence]:
        return [GeneralItemSequence(items=ctx.compiled_items)]

    def merge_outputs(self, ctx: LessonContext, outputs: list[TouchSequence]) -> LessonContext:
        result = outputs[-1] if outputs else TouchSequence(items=[])
        ctx.touch_sequence = result
        self._log(
            ctx,
            f"       {len(ctx.touches)} touches "
            f"across {ctx.config.lesson_blocks} blocks (profile: {ctx.config.profile})",
        )
        return ctx