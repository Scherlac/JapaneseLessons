from __future__ import annotations

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
        grammar_map = {g.id: g for g in progression}
        lesson_number = len(ctx.curriculum.get("lessons", [])) + 1
        noun_items = [lang_cfg.generator.convert_raw_noun(n) for n in ctx.nouns]
        verb_items = [lang_cfg.generator.convert_raw_verb(v) for v in ctx.verbs]

        # For multi-block lessons, project ahead: grammar covered in early blocks
        # unlocks dependents for later blocks within the same lesson.
        window = max(1, ctx.config.grammar_points_per_block)
        needed = window + max(ctx.config.lesson_blocks - 1, 0)
        effective_count = max(ctx.config.grammar_points_per_lesson, needed)
        projected = self._project_grammar(progression, covered, effective_count)

        prompt = lang_cfg.prompts.build_grammar_select_prompt(
            projected,
            noun_items,
            verb_items,
            lesson_number,
            covered_grammar_ids=covered,
            selection_count=effective_count,
        )
        result = PipelineGadgets.ask_llm(ctx, prompt)
        selected_ids: list[str] = result.get("selected_ids") or [
            g.id for g in projected[:effective_count]
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
    def _project_grammar(
        progression: list[GrammarItem],
        initial_covered: list[str],
        needed: int,
    ) -> list[GrammarItem]:
        """Return up to *needed* grammar items using simulated in-lesson unlocking.

        Starts from the currently-unlocked items, then simulates covering each
        selected item in turn so its dependents become available for later blocks
        within the same lesson.
        """
        simulated_covered = set(initial_covered)
        remaining = [g for g in progression if g.id not in simulated_covered]
        result: list[GrammarItem] = []
        while len(result) < needed and remaining:
            unlockable = sorted(
                [g for g in remaining if all(req in simulated_covered for req in g.requires)],
                key=lambda g: g.level,
            )
            if not unlockable:
                break
            chosen = unlockable[0]
            result.append(chosen)
            simulated_covered.add(chosen.id)
            remaining.remove(chosen)
        return result

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
