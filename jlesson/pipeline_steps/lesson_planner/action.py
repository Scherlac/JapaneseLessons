from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from jlesson.models import GeneralItem, GrammarItem

from ..pipeline_core import (
    ActionConfig,
    BlockOutline,
    LessonOutline,
    SelectedVocabSet,
    StepAction,
)
from .prompt import GrammarCoverageInfo, build_lesson_plan_prompt


@dataclass
class LessonPlannerChunk(SelectedVocabSet):
    """All data the lesson planner needs for one planning call."""

    block_index: int
    lesson_number: int
    lesson_blocks: int
    narrative_blocks: list[str]
    progression: list[GrammarItem]
    unlocked: list[GrammarItem]
    covered_grammar_ids: list[str]
    covered_grammar: list[GrammarCoverageInfo]


@dataclass
class LessonPlannerResult:
    """Two-pass lesson outline with resolved grammar items."""

    outline: LessonOutline
    selected_grammar: list[GrammarItem]
    selected_grammar_blocks: list[list[GrammarItem]]


def _project_grammar(
    progression: list[GrammarItem],
    initial_covered: list[str],
    needed: int,
) -> list[GrammarItem]:
    """Return up to *needed* grammar items using simulated in-lesson unlocking."""
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


class LessonPlannerAction(StepAction[LessonPlannerChunk, LessonPlannerResult]):
    """Two-pass lesson planner: draft outline → revised outline."""

    def run(self, config: ActionConfig, chunk: LessonPlannerChunk) -> LessonPlannerResult:
        grammar_map = {g.id: g for g in chunk.progression}

        common_kwargs: dict[str, Any] = dict(
            lesson_number=chunk.lesson_number,
            lesson_blocks=chunk.lesson_blocks,
            narrative_blocks=chunk.narrative_blocks,
            unlocked_grammar=chunk.unlocked,
            covered_grammar=chunk.covered_grammar,
            grammar_points_per_lesson=config.lesson.grammar_points_per_lesson,
            grammar_points_per_block=config.lesson.grammar_points_per_block,
            sentences_per_grammar=config.lesson.sentences_per_grammar,
            noun_names=[n.source.display_text for n in chunk.nouns],
            verb_names=[v.source.display_text for v in chunk.verbs],
        )

        # ── Pass 1: draft outline ────────────────────────────────────────
        prompt_1 = build_lesson_plan_prompt(**common_kwargs, previous_outline_json=None)
        result_1 = config.runtime.call_llm(prompt_1)

        # ── Pass 2: revised outline ──────────────────────────────────────
        pass_1_json = json.dumps(result_1, indent=2, ensure_ascii=False)
        prompt_2 = build_lesson_plan_prompt(**common_kwargs, previous_outline_json=pass_1_json)
        result_2 = config.runtime.call_llm(prompt_2)

        # ── Parse the final result ───────────────────────────────────────
        outline = self._parse_outline(result_2, chunk.lesson_blocks, config.lesson.sentences_per_grammar)
        selected_grammar = self._resolve_grammar(outline.grammar_ids, grammar_map)

        # Fill in from progression if LLM returned fewer than requested
        target = max(1, config.lesson.grammar_points_per_lesson)
        if len(selected_grammar) < target:
            already = [g.id for g in selected_grammar]
            additional = _project_grammar(
                chunk.progression,
                chunk.covered_grammar_ids + already,
                target - len(selected_grammar),
            )
            selected_grammar = selected_grammar + additional
            outline.grammar_ids = [g.id for g in selected_grammar]

        # Build per-block grammar lists from the outline
        selected_grammar_blocks = self._build_grammar_blocks(
            outline, grammar_map, chunk.lesson_blocks,
        )

        return LessonPlannerResult(
            outline=outline,
            selected_grammar=selected_grammar,
            selected_grammar_blocks=selected_grammar_blocks,
        )

    @staticmethod
    def _parse_outline(
        raw: dict,
        expected_blocks: int,
        default_sentence_count: int,
    ) -> LessonOutline:
        grammar_ids = raw.get("grammar_ids", [])
        rationale = raw.get("rationale", "")
        blocks: list[BlockOutline] = []
        for block_raw in raw.get("blocks", []):
            blocks.append(BlockOutline(
                block_index=block_raw.get("block_index", len(blocks) + 1),
                grammar_ids=block_raw.get("grammar_ids", []),
                noun_suggestions=block_raw.get("noun_suggestions", []),
                verb_suggestions=block_raw.get("verb_suggestions", []),
                sentence_count=block_raw.get("sentence_count", default_sentence_count),
                narrative_summary=block_raw.get("narrative_summary", ""),
            ))
        # Pad missing blocks
        while len(blocks) < expected_blocks:
            idx = len(blocks) + 1
            blocks.append(BlockOutline(
                block_index=idx,
                grammar_ids=grammar_ids[:1] if grammar_ids else [],
                noun_suggestions=[],
                verb_suggestions=[],
                sentence_count=default_sentence_count,
                narrative_summary="",
            ))
        return LessonOutline(blocks=blocks, grammar_ids=grammar_ids, rationale=rationale)

    @staticmethod
    def _resolve_grammar(
        ids: list[str],
        grammar_map: dict[str, GrammarItem],
    ) -> list[GrammarItem]:
        return [grammar_map[gid] for gid in ids if gid in grammar_map]

    @staticmethod
    def _build_grammar_blocks(
        outline: LessonOutline,
        grammar_map: dict[str, GrammarItem],
        expected_blocks: int,
    ) -> list[list[GrammarItem]]:
        result: list[list[GrammarItem]] = []
        for block in outline.blocks[:expected_blocks]:
            result.append([grammar_map[gid] for gid in block.grammar_ids if gid in grammar_map])
        while len(result) < expected_blocks:
            result.append([])
        return result
