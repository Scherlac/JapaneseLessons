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
        return ctx.touch_sequence is not None

    def build_input(self, ctx: LessonContext) -> GeneralItemSequence:
        items = []
        if ctx.lesson_plan is not None:
            for block in ctx.lesson_plan.blocks:
                for phase_items in block.content_sequences.values():
                    items.extend(phase_items)
        return GeneralItemSequence(items=items)

    def merge_output(self, ctx: LessonContext, outputs: TouchSequence) -> LessonContext:
        result = outputs if outputs else TouchSequence(items=[])
        ctx.touch_sequence = result
        self._log(
            ctx,
            f"       {len(result.items)} touches "
            f"across {ctx.config.lesson_blocks} blocks (profile: {ctx.config.profile})",
        )
        return ctx