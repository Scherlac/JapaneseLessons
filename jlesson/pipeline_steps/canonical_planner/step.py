from __future__ import annotations

from .action import (
    CanonicalPlannerAction, 
)
from ..pipeline_core import (
    ActionStep, LessonContext, NarrativeFrame, CanonicalLessonPlan
)

class CanonicalPlannerStep(ActionStep[NarrativeFrame, CanonicalLessonPlan]):
    """Canonical planner: draft outline then revise with Fibonacci pacing."""

    name = "canonical_planner"
    description = "LLM: plan canonical lesson"
    _action = CanonicalPlannerAction()

    @property
    def action(self) -> CanonicalPlannerAction:
        return self._action

    def should_skip(self, ctx: LessonContext) -> bool:
        if ctx.narrative_frame is None:
            self._log(ctx, "       no narrative frame — cannot plan canonical lesson")
            return True
        return False

    def build_input(self, ctx: LessonContext) -> NarrativeFrame:

        return ctx.narrative_frame

    def merge_output(
        self,
        ctx: LessonContext,
        output: CanonicalLessonPlan,
    ) -> LessonContext:
        
        ctx.canonical_plan = output
        self._log(ctx, f"       planned {len(ctx.canonical_plan.blocks)} canonical lesson blocks")
        for block in ctx.canonical_plan.blocks:
            self._log(ctx, f"         block {block.block_index}: "
                f"{len(block.grammar_ids)} grammar items")
            for seq_id, seq in block.content_sequences.items():
                self._log(ctx, f"           sequence {seq_id}: {len(seq)} items")

        return ctx
