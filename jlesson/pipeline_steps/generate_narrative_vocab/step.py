from __future__ import annotations

from jlesson.models import VocabFile

from ..pipeline_core import ActionStep, LessonContext, NarrativeVocabPlan
from .action import GenerateNarrativeVocabAction


class GenerateNarrativeVocabStep(ActionStep[NarrativeVocabPlan, VocabFile]):
    """Generate full vocab entries for terms extracted from the narrative.

    Inputs (from ``LessonContext``)
    --------------------------------
    narrative_vocab_terms   list[NarrativeVocabBlock]  (via ``NarrativeVocabPlan``)
        Produced by ``ExtractNarrativeVocabStep`` and stored in
        ``LessonContext.narrative_vocab_terms``.  ``build_chunks`` wraps these
        in a ``NarrativeVocabPlan`` — the same type ``ExtractNarrativeVocabStep``
        emits — making the inter-step dependency typed rather than implicit.

    Output
    ------
    vocab    VocabFile
        Full vocab entries with target-language forms, ready for
        ``SelectVocabStep``.
    """

    name = "generate_narrative_vocab"
    description = "LLM: generate vocab from narrative terms"

    @property
    def action(self) -> GenerateNarrativeVocabAction:
        return GenerateNarrativeVocabAction()

    def should_skip(self, ctx: LessonContext) -> bool:
        if ctx.vocab:
            self._log(ctx, "       using existing vocab")
            return True
        return False

    def build_chunks(self, ctx: LessonContext) -> list[NarrativeVocabPlan]:
        if not ctx.narrative_vocab_terms:
            return []
        return [NarrativeVocabPlan(blocks=ctx.narrative_vocab_terms)]

    def merge_outputs(self, ctx: LessonContext, outputs: list[VocabFile]) -> LessonContext:
        if not outputs:
            self._log(ctx, "       (no narrative vocab terms — skipping)")
            return ctx
        vocab = outputs[0]
        ctx.vocab = vocab
        self._log(
            ctx,
            f"       generated {len(vocab.nouns)} nouns, {len(vocab.verbs)} verbs from narrative",
        )
        return ctx
