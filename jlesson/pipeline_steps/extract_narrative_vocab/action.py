"""Stateless narrative vocabulary extraction action.

This module contains the pure transformation logic extracted from
``ExtractNarrativeVocabStep.execute``.  It has no knowledge of ``LessonContext``
and performs all I/O through ``config.runtime``, making it independently
testable with a mock runtime.
"""
from __future__ import annotations

from jlesson.models import NarrativeVocabBlock

from ..pipeline_core import ActionConfig, NarrativeFrame, NarrativeVocabPlan, StepAction


class ExtractNarrativeVocabAction(StepAction[NarrativeFrame, NarrativeVocabPlan]):
    """Extract per-block vocabulary targets from the narrative progression.

    Input
    -----
    chunk : NarrativeFrame
        The typed output of ``NarrativeGeneratorStep`` — the narrative blocks.
        Using ``NarrativeFrame`` as the chunk type makes the inter-step
        dependency explicit: this action directly consumes the artifact the
        preceding step produces.

    Output
    ------
    NarrativeVocabPlan
        Per-block noun/verb vocabulary targets wrapped in the typed inter-step
        artifact. One LLM call is made via ``config.runtime.call_llm``.
    """

    def run(self, config: ActionConfig, chunk: NarrativeFrame) -> NarrativeVocabPlan:
        prompt = config.language.prompts.build_narrative_vocab_extract_prompt(
            narrative_blocks=chunk.blocks,
            nouns_per_block=config.lesson.num_nouns,
            verbs_per_block=config.lesson.num_verbs,
        )
        result = config.runtime.call_llm(prompt)
        blocks: list[NarrativeVocabBlock] = []
        for block in result.get("blocks", []):
            if not isinstance(block, dict):
                continue
            nouns = self._normalize_terms(block.get("nouns", []), config.lesson.num_nouns)
            verbs = self._normalize_terms(block.get("verbs", []), config.lesson.num_verbs)
            blocks.append(NarrativeVocabBlock(nouns=nouns, verbs=verbs))

        while len(blocks) < len(chunk.blocks):
            blocks.append(NarrativeVocabBlock())
        return NarrativeVocabPlan(blocks=blocks[:len(chunk.blocks)])

    @staticmethod
    def _normalize_terms(raw_terms: list, limit: int) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for term in raw_terms or []:
            if not isinstance(term, str):
                continue
            clean = term.strip()
            key = clean.lower()
            if not clean or key in seen:
                continue
            normalized.append(clean)
            seen.add(key)
            if len(normalized) >= limit:
                break
        return normalized
