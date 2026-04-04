from __future__ import annotations

from ..pipeline_core import (
    ActionStep,
    CanonicalVocabSet,
    LessonContext,
    NarrativeVocabPlan,
)
from .action import CanonicalVocabSelectAction, CanonicalVocabSelectRequest


class CanonicalVocabSelectStep(ActionStep[CanonicalVocabSelectRequest, CanonicalVocabSet]):
    """Select canonical English vocabulary terms for the planning phase.

    Input (from ``LessonContext``)
    --------------------------------
    narrative_vocab_terms  list[NarrativeVocabBlock]
        Produced by ``ExtractNarrativeVocabStep``.  Wrapped in a
        ``NarrativeVocabPlan`` — the same typed artifact the preceding step
        emits — keeping the inter-step dependency explicit.

    Output
    ------
    canonical_vocab  CanonicalVocabSet
        English-only canonical item lists, one set per lesson block.
        No LLM calls are made; selection is purely deterministic
        (curriculum-coverage aware).

    This step runs **before** any language-specific generation and makes
    ``ctx.canonical_vocab`` available to ``LessonPlannerStep`` and
    ``GrammarSelectStep``.
    """

    name = "canonical_vocab_select"
    description = "Pick canonical English vocab terms for the planning phase"
    _action = CanonicalVocabSelectAction()

    @property
    def action(self) -> CanonicalVocabSelectAction:
        return self._action

    def should_skip(self, ctx: LessonContext) -> bool:
        if ctx.canonical_vocab is not None:
            self._log(ctx, "       using existing canonical vocab selection")
            return True
        return False

    def build_chunks(self, ctx: LessonContext) -> list[CanonicalVocabSelectRequest]:
        narrative_plan = NarrativeVocabPlan(blocks=list(ctx.narrative_vocab_terms))
        return [
            CanonicalVocabSelectRequest(
                narrative_plan=narrative_plan,
                covered_nouns=list(ctx.curriculum.covered_nouns),
                covered_verbs=list(ctx.curriculum.covered_verbs),
                num_nouns_per_block=ctx.config.num_nouns,
                num_verbs_per_block=ctx.config.num_verbs,
                lesson_blocks=ctx.config.lesson_blocks,
                narrative_blocks=list(ctx.narrative_blocks),
            )
        ]

    def merge_outputs(
        self,
        ctx: LessonContext,
        outputs: list[CanonicalVocabSet],
    ) -> LessonContext:
        ctx.canonical_vocab = outputs[0]
        noun_names = [n.text for n in ctx.canonical_vocab.nouns]
        verb_names = [v.text for v in ctx.canonical_vocab.verbs]
        self._log(ctx, f"       canonical nouns : {noun_names}")
        self._log(ctx, f"       canonical verbs : {verb_names}")
        return ctx
