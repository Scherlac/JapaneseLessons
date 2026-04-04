from __future__ import annotations

from dataclasses import dataclass

from jlesson.models import GrammarItem

from ..pipeline_core import ActionConfig, CanonicalVocabSet, StepAction


def _project_grammar(
    progression: list[GrammarItem],
    initial_covered: list[str],
    needed: int,
) -> list[GrammarItem]:
    """Return up to *needed* grammar items using simulated in-lesson unlocking."""
    simulated_covered = set(initial_covered)
    remaining = [grammar for grammar in progression if grammar.id not in simulated_covered]
    result: list[GrammarItem] = []
    while len(result) < needed and remaining:
        unlockable = sorted(
            [grammar for grammar in remaining if all(req in simulated_covered for req in grammar.requires)],
            key=lambda grammar: grammar.level,
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


@dataclass
class GrammarSelectChunk:
    """All data the grammar select action needs for one lesson-wide selection call."""

    canonical: CanonicalVocabSet
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


class GrammarSelectAction(StepAction[GrammarSelectChunk, GrammarSelectResult]):
    """Select grammar points via LLM then extend and slice for multi-block lessons."""

    def run(self, config: ActionConfig, chunk: GrammarSelectChunk) -> GrammarSelectResult:
        grammar_map = {grammar.id: grammar for grammar in chunk.progression}

        prompt = config.language.prompts.build_grammar_select_prompt(
            chunk.unlocked,
            [n.text for n in chunk.canonical.nouns],
            [v.text for v in chunk.canonical.verbs],
            chunk.lesson_number,
            covered_grammar_ids=chunk.covered_grammar_ids,
            selection_count=config.lesson.grammar_points_per_lesson,
        )
        result = config.runtime.call_llm(prompt)
        selected_ids: list[str] = result.get("selected_ids") or [
            grammar.id for grammar in chunk.unlocked[: config.lesson.grammar_points_per_lesson]
        ]

        selected_grammar: list[GrammarItem] = [
            grammar_map[selected_id] for selected_id in selected_ids if selected_id in grammar_map
        ]

        target_count = max(1, config.lesson.grammar_points_per_lesson)
        if not selected_grammar:
            selected_grammar = _project_grammar(
                chunk.progression,
                chunk.covered_grammar_ids,
                target_count,
            )
        elif len(selected_grammar) < target_count:
            already_selected_ids = [g.id for g in selected_grammar]
            additional = _project_grammar(
                chunk.progression,
                chunk.covered_grammar_ids + already_selected_ids,
                target_count - len(selected_grammar),
            )
            selected_grammar = selected_grammar + additional

        selected_grammar_blocks = _build_block_progression(
            selected_grammar,
            config.lesson.lesson_blocks,
            config.lesson.grammar_points_per_block,
        )
        return GrammarSelectResult(
            selected_grammar=selected_grammar,
            selected_grammar_blocks=selected_grammar_blocks,
        )