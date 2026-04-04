from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Tuple, List, Dict
from collections import Counter
from .prompt import GrammarCoverageInfo, fibonacci_stage_label

from jlesson.models import GrammarItem, CanonicalItem

from ...models import (
    Phase   
)

from ...language_config import LanguageConfig

from ..pipeline_core import (
    ActionConfig,
    StepAction,
    NarrativeFrame,
    CanonicalLessonPlan, 
    CanonicalLessonBlock    
)
from .prompt import GrammarCoverageInfo, build_lesson_plan_prompt


# test run:
#  conda activate base; jlesson lesson add --theme totoro --nouns 1 --verbs 1 --sentences 1 --grammar-points 3 --grammar-points-per-block 2 --blocks 5 --curriculum output/review_totoro/curriculum.json --output-dir output/review_totoro --no-retrieval --narrative-file .\narrative_totoro.txt

@dataclass
class LessonBlockConfig:
    """All data the cononical planner needs for one planning call."""

    block_index: int
    lesson_number: int
    lesson_blocks: int
    narrative_blocks: List[str]
    covered_grammar_ids: List[str]
    covered_grammar: List[GrammarCoverageInfo]


CanonicalPlannerOutput = List[CanonicalLessonBlock | None]


def _project_grammar(
    progression: List[GrammarItem],
    initial_covered: List[str],
    needed: int,
) -> List[GrammarItem]:
    """Return up to *needed* grammar items using simulated in-lesson unlocking."""
    simulated_covered = set(initial_covered)
    remaining = [g for g in progression if g.id not in simulated_covered]
    result: List[GrammarItem] = []
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


class CanonicalPlannerAction(StepAction[NarrativeFrame, CanonicalLessonPlan]):
    """Two-pass cononical planner: draft outline → revised outline."""

    def run(self, config: ActionConfig, input: NarrativeFrame) -> CanonicalLessonPlan:


        progression = list(config.language.grammar_progression)
        covered = config.curriculum.covered_grammar_ids
        unlocked = _project_grammar(progression, covered, config.lesson.grammar_points_per_lesson)

        # Count how many completed lessons each grammar point appeared in
        grammar_lesson_counts: Counter[str] = Counter()
        for lesson in config.curriculum.lessons:
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
        canonical = None
        if canonical is None:
            canonical = CanonicalLessonBlock(
                theme=config.lesson.theme,
                lesson_number=config.lesson.lesson_number,
                grammar_ids=[],
                content_sequences={},
            )



        common_kwargs: dict[str, Any] = dict(
            lesson_number=input.lesson_number,
            lesson_blocks=input.lesson_blocks,
            narrative_blocks=input.blocks,
            unlocked_grammar=unlocked,
            covered_grammar=covered_grammar,
            grammar_points_per_lesson=config.lesson.grammar_points_per_lesson,
            grammar_points_per_block=config.lesson.grammar_points_per_block,
            sentences_per_grammar=config.lesson.sentences_per_grammar,
            noun_names=[n.text for n in canonical.content_sequences.get(Phase.NOUNS, [])],
            verb_names=[v.text for v in canonical.content_sequences.get(Phase.VERBS, [])],
            canonical_language=config.language.canonical_language,
        )

        # ── Pass 1: draft outline ────────────────────────────────────────
        prompt_1 = build_lesson_plan_prompt(**common_kwargs, previous_outline_json=None)
        result_1 = config.runtime.call_llm(prompt_1)

        # ── Pass 2: revised outline ──────────────────────────────────────
        pass_1_json = json.dumps(result_1, indent=2, ensure_ascii=False)
        prompt_2 = build_lesson_plan_prompt(**common_kwargs, previous_outline_json=pass_1_json)
        result_2 = config.runtime.call_llm(prompt_2)

        # ── Parse the final result ───────────────────────────────────────
        outline = self._parse_outline(
            result_2,
            config.lesson.lesson_blocks,
            config.lesson.sentences_per_grammar,
            theme=config.lesson.theme,
            lesson_number=input.lesson_number,
        )
        return outline

    @staticmethod
    def _parse_outline(
        raw: dict,
        expected_blocks: int,
        default_sentence_count: int,
        *,
        theme: str = "",
        lesson_number: int = 0,
    ) -> CanonicalLessonPlan:
        
        grammar_ids = raw.get("grammar_ids", [])
        rationale = raw.get("rationale", "")
        blocks: List[CanonicalLessonBlock] = []
        for block_raw in raw.get("blocks", []):

            content_sequences = {}
            if "noun_suggestions" in block_raw:
                content_sequences[Phase.NOUNS] = [CanonicalItem(id=nid, text=nid) for nid in block_raw.get("noun_suggestions", [])]
            if "verb_suggestions" in block_raw:
                content_sequences[Phase.VERBS] = [CanonicalItem(id=vid, text=vid) for vid in block_raw.get("verb_suggestions", [])]
            if "adjective_suggestions" in block_raw:
                content_sequences[Phase.ADJECTIVES] = [CanonicalItem(id=aid, text=aid) for aid in block_raw.get("adjective_suggestions", [])]

            blocks.append(CanonicalLessonBlock(
                theme=theme,
                lesson_number=lesson_number,
                block_index=block_raw.get("block_index", len(blocks) + 1),
                grammar_ids=block_raw.get("grammar_ids", []),
                narrative_content=block_raw.get("narrative_summary", ""),
                content_sequences=content_sequences,
            ))
        # Pad missing blocks
        while len(blocks) < expected_blocks:
            idx = len(blocks) + 1
            blocks.append(CanonicalLessonBlock(
                theme=theme,
                lesson_number=lesson_number,
                block_index=idx,
                grammar_ids=grammar_ids[:1] if grammar_ids else [],
                content_sequences={
                    Phase.NOUNS: [],
                    Phase.VERBS: [],
                },
                narrative_content="",
            ))
        return CanonicalLessonPlan(theme=theme, lesson_number=lesson_number, blocks=blocks)


    @staticmethod
    def _build_grammar_blocks(
        outline: CanonicalLessonPlan,
        grammar_map: Dict[str, GrammarItem],
        expected_blocks: int,
    ) -> List[List[GrammarItem]]:
        result: List[List[GrammarItem]] = []
        for block in outline.blocks[:expected_blocks]:
            result.append([grammar_map[gid] for gid in block.grammar_ids if gid in grammar_map])
        while len(result) < expected_blocks:
            result.append([])
        return result
