from __future__ import annotations

from jlesson.vocab_generator._base import _normalize_vocab_item
from .pipeline_core import LessonContext, PipelineStep
from .pipeline_gadgets import PipelineGadgets


class GenerateNarrativeVocabStep(PipelineStep):
    """Generate full vocab entries for terms extracted from the narrative."""

    name = "generate_narrative_vocab"
    description = "LLM: generate vocab from narrative terms"
    BATCH_SIZE = 60

    def execute(self, ctx: LessonContext) -> LessonContext:
        if ctx.vocab:
            self._log(ctx, "       using existing vocab")
            return ctx
        if not ctx.narrative_vocab_terms:
            self._log(ctx, "       (no narrative vocab terms — skipping)")
            return ctx

        all_nouns: list[str] = []
        all_verbs: list[str] = []
        seen_nouns: set[str] = set()
        seen_verbs: set[str] = set()
        for block in ctx.narrative_vocab_terms:
            for term in block.get("nouns", []):
                key = term.lower()
                if key not in seen_nouns:
                    all_nouns.append(term)
                    seen_nouns.add(key)
            for term in block.get("verbs", []):
                key = term.lower()
                if key not in seen_verbs:
                    all_verbs.append(term)
                    seen_verbs.add(key)

        if not ctx.language_config:
            self._log(ctx, "       (no language config for generating vocab — skipping)")
            return ctx

        lc = ctx.language_config
        nouns: list[dict] = []
        verbs: list[dict] = []

        # Send nouns and verbs in paired batches so no single call is too large.
        max_batches = max(
            (len(all_nouns) + self.BATCH_SIZE - 1) // self.BATCH_SIZE,
            (len(all_verbs) + self.BATCH_SIZE - 1) // self.BATCH_SIZE,
            1,
        )
        for i in range(max_batches):
            noun_batch = all_nouns[i * self.BATCH_SIZE : (i + 1) * self.BATCH_SIZE]
            verb_batch = all_verbs[i * self.BATCH_SIZE : (i + 1) * self.BATCH_SIZE]
            if not ctx.language_config.prompts:
                self._log(ctx, "       (no prompt template for generating vocab — skipping)")
                break
            prompt = ctx.language_config.prompts.build_narrative_vocab_generate_prompt(
                nouns=noun_batch,
                verbs=verb_batch,
                theme=ctx.config.theme,
            )
            result = PipelineGadgets.ask_llm(ctx, prompt)
            nouns.extend(
                _normalize_vocab_item(n, lc)
                for n in result.get("nouns", [])
                if isinstance(n, dict) and n.get(lc.source.vocab_source_key) and n.get(lc.target.vocab_source_key)
            )
            verbs.extend(
                _normalize_vocab_item(v, lc)
                for v in result.get("verbs", [])
                if isinstance(v, dict) and v.get(lc.source.vocab_source_key) and v.get(lc.target.vocab_source_key)
            )

        ctx.vocab = {
            "theme": ctx.config.theme,
            "nouns": nouns,
            "verbs": verbs,
        }
        self._log(ctx, f"       generated {len(nouns)} nouns, {len(verbs)} verbs from narrative")
        return ctx
