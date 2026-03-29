from __future__ import annotations

from jlesson.models import GrammarItem
from jlesson.runtime import PipelineGadgets
from .pipeline_core import LessonContext, PipelineStep


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
        covered = ctx.curriculum.covered_grammar_ids
        grammar_map = {g.id: g for g in progression}
        lesson_number = len(ctx.curriculum.lessons) + 1
        noun_items = list(ctx.nouns)
        verb_items = list(ctx.verbs)

        # Ask LLM to pick only the starting grammar points from currently-unlocked items.
        # If the full progression has been covered, cycle back from the beginning.
        unlocked = self._project_grammar(progression, covered, ctx.config.grammar_points_per_lesson)
        if not unlocked:
            self._log(ctx, "       (grammar exhausted — cycling back from start)")
            covered = []
            unlocked = self._project_grammar(progression, covered, ctx.config.grammar_points_per_lesson)
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
                ctx.selected_grammar.append(grammar_map[selected_id])
            else:
                self._log(
                    ctx, f"       Warning: unknown grammar id {selected_id!r}, skipping"
                )

        # For multi-block lessons, extend the grammar chain programmatically so
        # each block can introduce new grammar points instead of repeating the same ones.
        window = max(1, ctx.config.grammar_points_per_block)
        needed = window + max(ctx.config.lesson_blocks - 1, 0)
        if len(ctx.selected_grammar) < needed:
            selected_ids_set = {g.id for g in ctx.selected_grammar}
            already_covered = list(covered) + list(selected_ids_set)
            additional = self._project_grammar(progression, already_covered, needed)
            for g in additional:
                if g.id not in selected_ids_set:
                    ctx.selected_grammar.append(g)
                    selected_ids_set.add(g.id)

        ctx.selected_grammar_blocks = self._build_block_progression(ctx)
        self._log(
            ctx,
            f"       selected : {[g.id for g in ctx.selected_grammar]}",
        )
        if ctx.selected_grammar_blocks:
            block_lines = "\n".join(
                f"         block {b + 1:>2}: {[g.id for g in block]}"
                for b, block in enumerate(ctx.selected_grammar_blocks)
            )
            self._log(ctx, f"       by block :\n{block_lines}")
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
    def _build_block_progression(ctx: LessonContext) -> list[list[GrammarItem]]:
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
