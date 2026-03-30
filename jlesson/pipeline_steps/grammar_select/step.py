from __future__ import annotations

from .action import GrammarSelectAction, GrammarSelectChunk, GrammarSelectResult, _project_grammar
from ..pipeline_core import ActionStep, LessonContext


class GrammarSelectStep(ActionStep[GrammarSelectChunk, GrammarSelectResult]):
    """Select the grammar progression slice for this lesson."""

    name = "grammar_select"
    description = "LLM: pick grammar points for this lesson"
    _action = GrammarSelectAction()

    @property
    def action(self) -> GrammarSelectAction:
        return self._action

    def should_skip(self, ctx: LessonContext) -> bool:
        if ctx.selected_grammar:
            self._log(ctx, "       using retrieved grammar")
            return True
        return False

    def build_chunks(self, ctx: LessonContext) -> list[GrammarSelectChunk]:
        progression = list(ctx.language_config.grammar_progression)
        covered = ctx.curriculum.covered_grammar_ids
        unlocked = _project_grammar(progression, covered, ctx.config.grammar_points_per_lesson)
        if not unlocked:
            self._log(ctx, "       (grammar exhausted — cycling back from start)")
            covered = []
            unlocked = _project_grammar(progression, covered, ctx.config.grammar_points_per_lesson)
        lesson_number = len(ctx.curriculum.lessons) + 1
        return [
            GrammarSelectChunk(
                vocab=ctx.vocab,
                nouns=list(ctx.nouns),
                verbs=list(ctx.verbs),
                block_index=0,
                progression=progression,
                unlocked=unlocked,
                covered_grammar_ids=covered,
                lesson_number=lesson_number,
            )
        ]

    def merge_outputs(
        self,
        ctx: LessonContext,
        outputs: list[GrammarSelectResult],
    ) -> LessonContext:
        result = outputs[0]
        ctx.selected_grammar = result.selected_grammar
        ctx.selected_grammar_blocks = result.selected_grammar_blocks
        self._log(ctx, f"       selected : {[grammar.id for grammar in ctx.selected_grammar]}")
        if ctx.selected_grammar_blocks:
            block_lines = "\n".join(
                f"         block {index + 1:>2}: {[grammar.id for grammar in block]}"
                for index, block in enumerate(ctx.selected_grammar_blocks)
            )
            self._log(ctx, f"       by block :\n{block_lines}")
        return ctx