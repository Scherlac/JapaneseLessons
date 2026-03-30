from __future__ import annotations

from dataclasses import dataclass

from jlesson.models import GrammarItem
from .pipeline_core import ActionConfig, ActionStep, LessonContext, SelectedVocabSet, StepAction


# ---------------------------------------------------------------------------
# Pure helper functions
# ---------------------------------------------------------------------------

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


def _build_block_progression(
    selected: list[GrammarItem],
    lesson_blocks: int,
    grammar_points_per_block: int,
) -> list[list[GrammarItem]]:
    if not selected:
        return []
    block_count = max(1, lesson_blocks)
    window = max(1, min(grammar_points_per_block, len(selected)))
    if block_count == 1:
        return [selected[:window]]
    max_start = max(len(selected) - window, 0)
    blocks: list[list[GrammarItem]] = []
    for block_index in range(block_count):
        if max_start == 0:
            start = 0
        else:
            start = int((block_index * max_start) / (block_count - 1))
        blocks.append(selected[start : start + window])
    return blocks


# ---------------------------------------------------------------------------
# Chunk and result types
# ---------------------------------------------------------------------------

@dataclass
class GrammarSelectChunk(SelectedVocabSet):
    """All data the grammar select action needs — one chunk per step execution.

    ``block_index`` is always 0 because grammar selection is a single LLM call
    that covers the whole lesson.
    """

    block_index: int
    progression: list[GrammarItem]
    unlocked: list[GrammarItem]
    covered_grammar_ids: list[str]
    lesson_number: int


@dataclass
class GrammarSelectResult:
    """Fully resolved grammar selection: flat list and per-block slices."""

    selected_grammar: list[GrammarItem]
    selected_grammar_blocks: list[list[GrammarItem]]


# ---------------------------------------------------------------------------
# Action
# ---------------------------------------------------------------------------

class GrammarSelectAction(StepAction[GrammarSelectChunk, GrammarSelectResult]):
    """Select grammar points via LLM then extend and slice for multi-block lessons.

    Single LLM call per lesson execution:

    1. Build a prompt from the unlocked grammar items, current nouns/verbs, and
       lesson number.
    2. Parse the LLM's ``selected_ids`` list; fall back to the first
       ``grammar_points_per_lesson`` unlocked items when the LLM response is
       empty.
    3. Extend the selection programmatically so multi-block lessons can
       introduce new grammar in each block (using :func:`_project_grammar`).
    4. Slice the extended selection into per-block windows via
       :func:`_build_block_progression`.
    """

    def run(self, config: ActionConfig, chunk: GrammarSelectChunk) -> GrammarSelectResult:
        grammar_map = {g.id: g for g in chunk.progression}

        prompt = config.language.prompts.build_grammar_select_prompt(
            chunk.unlocked,
            list(chunk.nouns),
            list(chunk.verbs),
            chunk.lesson_number,
            covered_grammar_ids=chunk.covered_grammar_ids,
            selection_count=config.lesson.grammar_points_per_lesson,
        )
        result = config.runtime.call_llm(prompt)
        selected_ids: list[str] = result.get("selected_ids") or [
            g.id for g in chunk.unlocked[: config.lesson.grammar_points_per_lesson]
        ]

        selected_grammar: list[GrammarItem] = [
            grammar_map[sid] for sid in selected_ids if sid in grammar_map
        ]

        # Extend for multi-block lessons so each block can introduce new grammar.
        window = max(1, config.lesson.grammar_points_per_block)
        needed = window + max(config.lesson.lesson_blocks - 1, 0)
        if len(selected_grammar) < needed:
            selected_ids_set = {g.id for g in selected_grammar}
            already_covered = list(chunk.covered_grammar_ids) + list(selected_ids_set)
            additional = _project_grammar(chunk.progression, already_covered, needed)
            for g in additional:
                if g.id not in selected_ids_set:
                    selected_grammar.append(g)
                    selected_ids_set.add(g.id)

        selected_grammar_blocks = _build_block_progression(
            selected_grammar,
            config.lesson.lesson_blocks,
            config.lesson.grammar_points_per_block,
        )
        return GrammarSelectResult(
            selected_grammar=selected_grammar,
            selected_grammar_blocks=selected_grammar_blocks,
        )


# ---------------------------------------------------------------------------
# Step
# ---------------------------------------------------------------------------

class GrammarSelectStep(ActionStep[GrammarSelectChunk, GrammarSelectResult]):
    """Select the grammar progression slice for this lesson.

    Inputs (from ``LessonContext``)
    --------------------------------
    curriculum.covered_grammar_ids  list[str]
        Grammar point IDs already introduced in past lessons.
    nouns / verbs                   list[GeneralItem]
        Selected lesson vocab, passed to the LLM prompt for context.
    config.grammar_points_per_lesson / grammar_points_per_block / lesson_blocks
        Sizing parameters.

    Outputs
    -------
    selected_grammar        list[GrammarItem]
        Flat list of grammar items chosen for this lesson.
    selected_grammar_blocks list[list[GrammarItem]]
        Per-block grammar slices derived from the flat list.

    Implementation
    --------------
    Grammar exhaustion (all points covered) is detected in ``build_chunks``
    and handled by cycling back from the start of the progression with an
    empty ``covered_grammar_ids`` list.

    The single ``GrammarSelectAction`` call performs the LLM request plus all
    deterministic post-processing (selection extension and block slicing).
    """

    name = "grammar_select"
    description = "LLM: pick grammar points for this lesson"

    @property
    def action(self) -> GrammarSelectAction:
        return GrammarSelectAction()

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
        return [GrammarSelectChunk(
            vocab=ctx.vocab,
            nouns=list(ctx.nouns),
            verbs=list(ctx.verbs),
            block_index=0,
            progression=progression,
            unlocked=unlocked,
            covered_grammar_ids=covered,
            lesson_number=lesson_number,
        )]

    def merge_outputs(
        self, ctx: LessonContext, outputs: list[GrammarSelectResult]
    ) -> LessonContext:
        result = outputs[0]
        ctx.selected_grammar = result.selected_grammar
        ctx.selected_grammar_blocks = result.selected_grammar_blocks
        self._log(ctx, f"       selected : {[g.id for g in ctx.selected_grammar]}")
        if ctx.selected_grammar_blocks:
            block_lines = "\n".join(
                f"         block {b + 1:>2}: {[g.id for g in block]}"
                for b, block in enumerate(ctx.selected_grammar_blocks)
            )
            self._log(ctx, f"       by block :\n{block_lines}")
        return ctx

