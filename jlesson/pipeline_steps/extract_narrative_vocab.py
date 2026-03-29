from __future__ import annotations

from jlesson.models import NarrativeVocabBlock
from jlesson.runtime import PipelineRuntime
from .pipeline_core import LessonContext, PipelineStep


class ExtractNarrativeVocabStep(PipelineStep):
    """Extract block-level vocabulary targets from the narrative progression."""

    name = "extract_narrative_vocab"
    description = "LLM: extract block-level vocab from narrative"

    def execute(self, ctx: LessonContext) -> LessonContext:
        if ctx.narrative_vocab_terms:
            self._log(ctx, "       using existing narrative vocab targets")
            return ctx
        if not ctx.narrative_blocks:
            self._log(ctx, "       (no narrative blocks)")
            return ctx

        prompt = ctx.language_config.prompts.build_narrative_vocab_extract_prompt(
            narrative_blocks=ctx.narrative_blocks,
            nouns_per_block=ctx.config.num_nouns,
            verbs_per_block=ctx.config.num_verbs,
        )
        result = PipelineRuntime.ask_llm(ctx, prompt)
        blocks: list[NarrativeVocabBlock] = []
        for block in result.get("blocks", []):
            if not isinstance(block, dict):
                continue
            nouns = self._normalize_terms(block.get("nouns", []), ctx.config.num_nouns)
            verbs = self._normalize_terms(block.get("verbs", []), ctx.config.num_verbs)
            blocks.append(NarrativeVocabBlock(nouns=nouns, verbs=verbs))

        while len(blocks) < ctx.config.lesson_blocks:
            blocks.append(NarrativeVocabBlock())
        ctx.narrative_vocab_terms = blocks[: ctx.config.lesson_blocks]
        self._log(ctx, f"       {len(ctx.narrative_vocab_terms)} block vocab plans")
        return ctx

    @staticmethod
    def _normalize_terms(raw_terms, limit: int) -> list[str]:
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
