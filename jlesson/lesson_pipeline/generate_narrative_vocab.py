from __future__ import annotations

from .pipeline_core import LessonContext, PipelineStep
from .pipeline_gadgets import PipelineGadgets


class GenerateNarrativeVocabStep(PipelineStep):
    """Generate full Japanese vocab entries for terms extracted from the narrative."""

    name = "generate_narrative_vocab"
    description = "LLM: generate Japanese vocab from narrative terms"

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

        prompt = ctx.language_config.prompts.build_narrative_vocab_generate_prompt(
            nouns=all_nouns,
            verbs=all_verbs,
            theme=ctx.config.theme,
        )
        result = PipelineGadgets.ask_llm(ctx, prompt)

        nouns = [n for n in result.get("nouns", []) if isinstance(n, dict) and n.get("english") and n.get("japanese")]
        verbs = [v for v in result.get("verbs", []) if isinstance(v, dict) and v.get("english") and v.get("japanese")]

        ctx.vocab = {
            "theme": ctx.config.theme,
            "nouns": nouns,
            "verbs": verbs,
        }
        self._log(ctx, f"       generated {len(nouns)} nouns, {len(verbs)} verbs from narrative")
        return ctx
