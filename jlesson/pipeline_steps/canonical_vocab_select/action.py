"""Canonical vocabulary selection action.

Selects English canonical vocabulary terms for the lesson planning phase
without any language-specific LLM calls.  The output is a
``CanonicalVocabSelection`` that drives ``LessonPlannerStep`` and
``GrammarSelectStep`` entirely in English.
"""

from __future__ import annotations

from dataclasses import dataclass

from jlesson.models import CanonicalItem, NarrativeVocabBlock

from ..pipeline_core import (
    ActionConfig,
    CanonicalVocabSelection,
    NarrativeVocabPlan,
    StepAction,
)


@dataclass
class CanonicalVocabSelectRequest:
    """All data the canonical vocab select action needs.

    This directly consumes ``NarrativeVocabPlan`` — the typed output of
    ``ExtractNarrativeVocabStep`` — keeping the inter-step dependency typed.
    """

    narrative_plan: NarrativeVocabPlan
    covered_nouns: list[str]    # canonical English terms already in curriculum
    covered_verbs: list[str]
    num_nouns_per_block: int
    num_verbs_per_block: int
    lesson_blocks: int
    narrative_blocks: list[str]  # English narrative text per block (for context field)


class CanonicalVocabSelectAction(
    StepAction[CanonicalVocabSelectRequest, CanonicalVocabSelection]
):
    """Select canonical English vocabulary terms — no LLM calls.

    Iterates through the per-block term lists from ``NarrativeVocabPlan``,
    filters out curriculum-covered terms, picks up to
    ``num_nouns_per_block`` / ``num_verbs_per_block`` fresh terms per block,
    and records the per-block assignments in ``nouns_per_block`` /
    ``verbs_per_block`` for later use by ``SelectVocabStep``.
    """

    def run(
        self, config: ActionConfig, chunk: CanonicalVocabSelectRequest
    ) -> CanonicalVocabSelection:
        covered_nouns = {self._normalize(t) for t in chunk.covered_nouns}
        covered_verbs = {self._normalize(t) for t in chunk.covered_verbs}

        all_nouns: list[CanonicalItem] = []
        all_verbs: list[CanonicalItem] = []
        nouns_per_block: list[list[str]] = []
        verbs_per_block: list[list[str]] = []
        seen_nouns: set[str] = set()
        seen_verbs: set[str] = set()

        for block_index in range(chunk.lesson_blocks):
            block: NarrativeVocabBlock = (
                chunk.narrative_plan.blocks[block_index]
                if block_index < len(chunk.narrative_plan.blocks)
                else NarrativeVocabBlock()
            )
            narrative_text = (
                chunk.narrative_blocks[block_index]
                if block_index < len(chunk.narrative_blocks)
                else ""
            )

            block_nouns = self._pick_terms(
                block.nouns,
                covered=covered_nouns,
                seen=seen_nouns,
                limit=chunk.num_nouns_per_block,
                concept_type="noun",
                context=narrative_text,
                accumulator=all_nouns,
            )
            block_verbs = self._pick_terms(
                block.verbs,
                covered=covered_verbs,
                seen=seen_verbs,
                limit=chunk.num_verbs_per_block,
                concept_type="verb",
                context=narrative_text,
                accumulator=all_verbs,
            )

            nouns_per_block.append([item.text for item in block_nouns])
            verbs_per_block.append([item.text for item in block_verbs])

        return CanonicalVocabSelection(
            nouns=all_nouns,
            verbs=all_verbs,
            nouns_per_block=nouns_per_block,
            verbs_per_block=verbs_per_block,
        )

    @staticmethod
    def _normalize(term: str) -> str:
        return (term or "").strip().lower()

    def _pick_terms(
        self,
        terms: list[str],
        *,
        covered: set[str],
        seen: set[str],
        limit: int,
        concept_type: str,
        context: str,
        accumulator: list[CanonicalItem],
    ) -> list[CanonicalItem]:
        """Select up to *limit* fresh terms, add them to *accumulator*, return block slice."""
        block_items: list[CanonicalItem] = []
        for term in terms:
            if len(block_items) >= limit:
                break
            key = self._normalize(term)
            if not key or key in seen:
                continue
            item = CanonicalItem(
                text=term,
                concept_type=concept_type,
                context=context,
            )
            # Prefer uncovered terms; if all are covered fall back below.
            if key not in covered:
                block_items.append(item)
                accumulator.append(item)
                seen.add(key)

        # Gap-fill from covered terms when fresh ones are exhausted.
        if len(block_items) < limit:
            for term in terms:
                if len(block_items) >= limit:
                    break
                key = self._normalize(term)
                if not key or key in seen:
                    continue
                item = CanonicalItem(
                    text=term,
                    concept_type=concept_type,
                    context=context,
                )
                block_items.append(item)
                accumulator.append(item)
                seen.add(key)

        return block_items
