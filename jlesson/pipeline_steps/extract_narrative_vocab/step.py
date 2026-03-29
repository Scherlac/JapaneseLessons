from __future__ import annotations

from jlesson.models import NarrativeVocabBlock

from ..pipeline_core import ActionStep, LessonContext, NarrativeFrame
from .action import ExtractNarrativeVocabAction


class ExtractNarrativeVocabStep(ActionStep[NarrativeFrame, list[NarrativeVocabBlock]]):
    """Extract per-block vocabulary targets from the narrative progression.

    Inputs (from ``LessonContext``)
    --------------------------------
    narrative_blocks    list[str]
        Produced by ``NarrativeGeneratorStep`` and written to
        ``LessonContext.narrative_blocks``.  ``build_chunks`` wraps these in a
        ``NarrativeFrame`` — the same type that ``NarrativeGeneratorStep``
        emits — making the inter-step dependency typed rather than implicit.

    Output
    ------
    narrative_vocab_terms   list[NarrativeVocabBlock]
        Per-block noun/verb vocabulary hints consumed by ``SelectVocabStep``.
    """

    name = "extract_narrative_vocab"
    description = "LLM: extract block-level vocab from narrative"

    @property
    def action(self) -> ExtractNarrativeVocabAction:
        return ExtractNarrativeVocabAction()

    def should_skip(self, ctx: LessonContext) -> bool:
        if ctx.narrative_vocab_terms:
            self._log(ctx, "       using existing narrative vocab targets")
            return True
        return False

    def build_chunks(self, ctx: LessonContext) -> list[NarrativeFrame]:
        if not ctx.narrative_blocks:
            return []
        return [NarrativeFrame(blocks=ctx.narrative_blocks)]

    def merge_outputs(
        self, ctx: LessonContext, outputs: list[list[NarrativeVocabBlock]]
    ) -> LessonContext:
        if not outputs:
            self._log(ctx, "       (no narrative blocks — skipping vocab extraction)")
            return ctx
        ctx.narrative_vocab_terms = outputs[0]
        self._log(ctx, f"       {len(ctx.narrative_vocab_terms)} block vocab plans")
        return ctx
