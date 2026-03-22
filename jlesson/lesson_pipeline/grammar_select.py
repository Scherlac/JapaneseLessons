from __future__ import annotations

from jlesson.curriculum import get_next_grammar_from
from jlesson.models import GrammarItem
from .pipeline_core import LessonContext, PipelineStep
from .pipeline_grammar import grammar_id
from .pipeline_gadgets import PipelineGadgets


class GrammarSelectStep(PipelineStep):
    """Select the grammar progression slice for this lesson."""

    name = "grammar_select"
    description = "LLM: pick grammar points for this lesson"

    def execute(self, ctx: LessonContext) -> LessonContext:
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
            selection_count=ctx.config.grammar_points_per_lesson,
        )
        result = PipelineGadgets.ask_llm(ctx, prompt)
        selected_ids: list[str] = result.get("selected_ids") or [
            g.id for g in unlocked[: ctx.config.grammar_points_per_lesson]
        ]
        ctx.selected_grammar = []
        for selected_id in selected_ids:
            if selected_id in grammar_map:
                ctx.selected_grammar.append(grammar_map[selected_id].model_dump())
            else:
                self._log(
                    ctx, f"       Warning: unknown grammar id {selected_id!r}, skipping"
                )
        ctx.selected_grammar_blocks = self._build_block_progression(ctx)
        self._log(
            ctx,
            f"       selected : {[grammar_id(g) for g in ctx.selected_grammar]}",
        )
        if ctx.selected_grammar_blocks:
            block_plan = [
                [grammar_id(g) for g in block]
                for block in ctx.selected_grammar_blocks
            ]
            self._log(ctx, f"       by block : {block_plan}")
        return ctx

    @staticmethod
    def _build_block_progression(ctx: LessonContext) -> list[list[GrammarItem | dict]]:
        selected = list(ctx.selected_grammar)
        if not selected:
            return []

        block_count = max(1, ctx.config.lesson_blocks)
        window = max(1, min(ctx.config.grammar_points_per_block, len(selected)))
        if block_count == 1:
            return [selected[:window]]

        max_start = max(len(selected) - window, 0)
        blocks: list[list[GrammarItem | dict]] = []
        for block_index in range(block_count):
            if max_start == 0:
                start = 0
            else:
                start = int((block_index * max_start) / (block_count - 1))
            blocks.append(selected[start:start + window])
        return blocks
