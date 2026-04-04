from __future__ import annotations

from collections import Counter

from .action import LessonPlannerAction, LessonPlannerChunk, LessonPlannerResult, _project_grammar
from .prompt import GrammarCoverageInfo, fibonacci_stage_label
from ..pipeline_core import ActionStep, GrammarSelectionArtifact, LessonContext


class LessonPlannerStep(ActionStep[LessonPlannerChunk, LessonPlannerResult]):
    """Two-pass lesson planner: draft outline then revise with Fibonacci pacing."""

    name = "lesson_planner"
    description = "LLM: plan lesson outline (two-pass)"
    _action = LessonPlannerAction()

    @property
    def action(self) -> LessonPlannerAction:
        return self._action

    def should_skip(self, ctx: LessonContext) -> bool:
        if ctx.lesson_outline is not None:
            self._log(ctx, "       using existing lesson outline")
            return True
        return False

    def build_chunks(self, ctx: LessonContext) -> list[LessonPlannerChunk]:
        language_config = ctx.language_config
        assert language_config is not None
        progression = list(language_config.grammar_progression)
        covered = ctx.curriculum.covered_grammar_ids
        unlocked = _project_grammar(progression, covered, ctx.config.grammar_points_per_lesson)
        if not unlocked:
            self._log(ctx, "       (grammar exhausted — cycling back from start)")
            covered = []
            unlocked = _project_grammar(progression, covered, ctx.config.grammar_points_per_lesson)

        # Count how many completed lessons each grammar point appeared in
        grammar_lesson_counts: Counter[str] = Counter()
        for lesson in ctx.curriculum.lessons:
            if lesson.status == "completed":
                grammar_lesson_counts.update(lesson.grammar_ids)
        covered_grammar = [
            GrammarCoverageInfo(
                grammar_id=gid,
                lessons_seen=grammar_lesson_counts.get(gid, 0),
                fibonacci_label=fibonacci_stage_label(grammar_lesson_counts.get(gid, 0)),
            )
            for gid in covered
        ]

        lesson_number = len(ctx.curriculum.lessons) + 1
        if ctx.canonical_vocab is None:
            raise RuntimeError(
                "canonical_vocab is not set — CanonicalVocabSelectStep must run before LessonPlannerStep"
            )
        return [
            LessonPlannerChunk(
                canonical=ctx.canonical_vocab,
                block_index=0,
                lesson_number=lesson_number,
                lesson_blocks=ctx.config.lesson_blocks,
                narrative_blocks=list(ctx.narrative_blocks),
                progression=progression,
                unlocked=unlocked,
                covered_grammar_ids=covered,
                covered_grammar=covered_grammar,
            )
        ]

    def merge_outputs(
        self,
        ctx: LessonContext,
        outputs: list[LessonPlannerResult],
    ) -> LessonContext:
        result = outputs[0]
        ctx.grammar_selection = GrammarSelectionArtifact(
            selected_grammar=list(result.selected_grammar),
            selected_grammar_blocks=[list(block) for block in result.selected_grammar_blocks],
            lesson_outline=result.outline,
            canonical_plan=result.canonical_plan,
        )
        self._log(ctx, f"       selected : {[g.id for g in ctx.selected_grammar]}")
        self._log(ctx, f"       rationale: {result.outline.rationale}")
        if ctx.selected_grammar_blocks:
            block_lines = "\n".join(
                f"         block {i + 1:>2}: {[g.id for g in block]}"
                for i, block in enumerate(ctx.selected_grammar_blocks)
            )
            self._log(ctx, f"       by block :\n{block_lines}")
        return ctx
