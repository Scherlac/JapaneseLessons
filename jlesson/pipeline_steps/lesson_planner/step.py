"""Step: resolve canonical plan into language-specific lesson plan."""

from __future__ import annotations

from .action import LessonPlannerAction
from ..pipeline_core import (
    ActionStep,
    LessonContext,
    CanonicalLessonBlock,
    CanonicalLessonPlan,
    LessonBlock,
    LessonPlan,
)


class LessonPlannerStep(ActionStep[CanonicalLessonBlock, LessonBlock]):
    """Resolve each canonical block into language-specific content via LLM.

    Uses ``build_input_list`` to fan out over ``CanonicalLessonBlock``s and
    ``merge_output_list`` to reassemble the results into a ``LessonPlan``.
    """

    name = "lesson_planner"
    description = "LLM: resolve canonical items into target language"
    _action = LessonPlannerAction()

    @property
    def action(self) -> LessonPlannerAction:
        return self._action

    def should_skip(self, ctx: LessonContext) -> bool:
        if ctx.canonical_plan is None:
            self._log(ctx, "       no canonical plan — cannot resolve items")
            return True
        return False

    # -- single-input path (unused, required by ABC) -----------------------

    def build_input(self, ctx: LessonContext) -> CanonicalLessonBlock:
        # Not used — build_input_list is the primary path
        return ctx.canonical_plan.blocks[0]

    def merge_output(self, ctx: LessonContext, output: LessonBlock) -> LessonContext:
        # Not used — merge_output_list is the primary path
        return ctx

    # -- list-input path (primary) -----------------------------------------

    def build_input_list(self, ctx: LessonContext) -> list[CanonicalLessonBlock]:
        return list(ctx.canonical_plan.blocks)

    def merge_output_list(
        self,
        ctx: LessonContext,
        outputs: list[LessonBlock],
    ) -> LessonContext:
        plan = ctx.canonical_plan
        ctx.lesson_plan = LessonPlan(
            theme=plan.theme,
            lesson_number=plan.lesson_number,
            blocks=outputs,
        )
        self._log(
            ctx,
            f"       resolved {len(outputs)} blocks into target language",
        )
        for block in outputs:
            phases = ", ".join(
                f"{p.value}:{len(items)}"
                for p, items in block.content_sequences.items()
            )
            self._log(ctx, f"         block {block.block_index}: {phases}")
        return ctx
