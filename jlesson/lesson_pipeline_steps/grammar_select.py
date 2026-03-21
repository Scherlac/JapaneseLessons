from __future__ import annotations

from jlesson.curriculum import get_next_grammar_from

from .runtime import lesson_pipeline_module


class GrammarSelectStep(lesson_pipeline_module().PipelineStep):
    """Step 2 — LLM: select 1-2 grammar points for this lesson."""

    name = "grammar_select"
    description = "LLM: pick 1-2 grammar points for this lesson"

    def execute(self, ctx: lesson_pipeline_module().LessonContext) -> lesson_pipeline_module().LessonContext:
        if ctx.selected_grammar:
            self._log(ctx, "       using retrieved grammar")
            return ctx
        lang_cfg = ctx.language_config
        progression = list(lang_cfg.grammar_progression)
        covered = ctx.curriculum.get("covered_grammar_ids", [])
        unlocked = get_next_grammar_from(progression, covered)
        grammar_map = {g.id: g for g in progression}
        lesson_number = len(ctx.curriculum.get("lessons", [])) + 1
        noun_items = [lang_cfg.generator.convert_raw_noun(n) for n in ctx.nouns]
        verb_items = [lang_cfg.generator.convert_raw_verb(v) for v in ctx.verbs]
        prompt = lang_cfg.prompts.build_grammar_select_prompt(
            unlocked,
            noun_items,
            verb_items,
            lesson_number,
            covered_grammar_ids=covered,
        )
        result = lesson_pipeline_module().PipelineGadgets.ask_llm(ctx, prompt)
        selected_ids: list[str] = result.get("selected_ids") or [
            g.id for g in unlocked[:2]
        ]
        pipeline = lesson_pipeline_module()
        ctx.selected_grammar = []
        for grammar_id in selected_ids:
            if grammar_id in grammar_map:
                ctx.selected_grammar.append(grammar_map[grammar_id].model_dump())
            else:
                self._log(
                    ctx, f"       Warning: unknown grammar id {grammar_id!r}, skipping"
                )
        self._log(
            ctx,
            f"       selected : {[pipeline.PipelineGadgets.grammar_id(g) for g in ctx.selected_grammar]}",
        )
        return ctx