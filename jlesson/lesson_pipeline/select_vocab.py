from __future__ import annotations

from pathlib import Path

from jlesson.curriculum import suggest_new_vocab
from .pipeline_core import LessonContext, PipelineStep
from .pipeline_vocab import load_vocab


class SelectVocabStep(PipelineStep):
    """Step 1 — Load vocab file and select fresh nouns/verbs."""

    name = "select_vocab"
    description = "Pick fresh nouns/verbs from the vocab file"

    def execute(self, ctx: LessonContext) -> LessonContext:
        if ctx.nouns and ctx.verbs:
            self._log(ctx, "       using retrieved vocabulary")
            return ctx
        vocab_dir = Path(__file__).parent.parent / ctx.language_config.vocab_dir
        ctx.vocab = load_vocab(ctx.config.theme, vocab_dir)
        requested_nouns = ctx.config.num_nouns * ctx.config.lesson_blocks
        requested_verbs = ctx.config.num_verbs * ctx.config.lesson_blocks
        ctx.nouns, ctx.verbs = suggest_new_vocab(
            ctx.vocab["nouns"],
            ctx.vocab["verbs"],
            covered_nouns=ctx.curriculum.get("covered_nouns", []),
            covered_verbs=ctx.curriculum.get("covered_verbs", []),
            num_nouns=requested_nouns,
            num_verbs=requested_verbs,
            seed=ctx.config.seed,
        )
        self._log(ctx, f"       nouns : {[n['english'] for n in ctx.nouns]}")
        self._log(ctx, f"       verbs : {[v['english'] for v in ctx.verbs]}")
        return ctx