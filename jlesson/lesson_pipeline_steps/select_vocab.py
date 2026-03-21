from __future__ import annotations

from pathlib import Path

from .runtime import lesson_pipeline_module


class SelectVocabStep(lesson_pipeline_module().PipelineStep):
    """Step 1 — Load vocab file and select fresh nouns/verbs."""

    name = "select_vocab"
    description = "Pick fresh nouns/verbs from the vocab file"

    def execute(self, ctx: lesson_pipeline_module().LessonContext) -> lesson_pipeline_module().LessonContext:
        if ctx.nouns and ctx.verbs:
            self._log(ctx, "       using retrieved vocabulary")
            return ctx
        pipeline = lesson_pipeline_module()
        vocab_dir = Path(pipeline.__file__).parent.parent / ctx.language_config.vocab_dir
        ctx.vocab = pipeline._load_vocab(ctx.config.theme, vocab_dir)
        ctx.nouns, ctx.verbs = pipeline.suggest_new_vocab(
            ctx.vocab["nouns"],
            ctx.vocab["verbs"],
            covered_nouns=ctx.curriculum.get("covered_nouns", []),
            covered_verbs=ctx.curriculum.get("covered_verbs", []),
            num_nouns=ctx.config.num_nouns,
            num_verbs=ctx.config.num_verbs,
            seed=ctx.config.seed,
        )
        self._log(ctx, f"       nouns : {[n['english'] for n in ctx.nouns]}")
        self._log(ctx, f"       verbs : {[v['english'] for v in ctx.verbs]}")
        return ctx