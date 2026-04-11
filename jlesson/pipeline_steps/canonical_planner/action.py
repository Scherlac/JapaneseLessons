from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Tuple, List, Dict
from collections import Counter
from .prompt import PHASE_PARSE_DETAILS, GrammarCoverageInfo, fibonacci_stage_label

from jlesson.models import GrammarItem, CanonicalItem

from ...models import (
    Phase   
)

from ...language_config import LanguageConfig

from ..pipeline_core import (
    ActionConfig,
    EmptyNarrativeBlock,
    NarrativeBlock,
    StepAction,
    NarrativeFrame,
    CanonicalLessonPlan, 
    CanonicalLessonBlock    
)
from .prompt import GrammarCoverageInfo, build_lesson_plan_prompt


# test run:
#  conda activate base; jlesson lesson add --theme totoro --nouns 1 --verbs 1 --sentences 1 --grammar-points 3 --grammar-points-per-block 2 --blocks 5 --curriculum output/review_totoro/curriculum.json --output-dir output/review_totoro --narrative-file .\narrative_totoro.txt


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

        # Build a lookup of covered grammar items for reinforcement.
        # Include any covered grammar point that is not yet mastered (< 21 lessons seen)
        # so the LLM can include them in blocks alongside newly unlocked points.
        MASTERY_THRESHOLD = 21
        grammar_by_id: Dict[str, GrammarItem] = {g.id: g for g in progression}
        reinforcement_grammar: List[GrammarItem] = [
            grammar_by_id[gid]
            for gid in covered
            if gid in grammar_by_id and grammar_lesson_counts.get(gid, 0) < MASTERY_THRESHOLD
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
            reinforcement_grammar=reinforcement_grammar,
            grammar_points_per_lesson=config.lesson.grammar_points_per_lesson,
            grammar_points_per_block=config.lesson.grammar_points_per_block,
            content_counts={
                Phase.NOUNS: config.lesson.num_nouns,
                Phase.VERBS: config.lesson.num_verbs,
                Phase.ADJECTIVES: config.lesson.num_adjectives,
                Phase.GRAMMAR: config.lesson.sentences_per_grammar * config.lesson.grammar_points_per_block,
                Phase.NARRATIVE: 0,
            },
            content_sequences=canonical.content_sequences,
            canonical_language=config.language.canonical_language,
        )

        # Collect already-seen vocabulary from RCM to prevent cross-lesson repetition
        if config.rcm is not None:
            lang = config.language.code
            vocab_phases = (Phase.NOUNS, Phase.VERBS, Phase.ADJECTIVES)
            # Canonical text -> set[gloss] for gloss-aware dedup
            covered_vocab: dict[Phase, dict[str, set[str]]] | None = {
                phase: config.rcm.covered_vocab(lang, phase)
                for phase in vocab_phases
            }
            # Also merge target-language texts so we catch same target word from two English entries
            for phase in vocab_phases:
                target_texts = config.rcm.covered_target_texts(lang, phase)
                for tgt in target_texts:
                    covered_vocab[phase].setdefault(tgt, set())
            # Drop phases where nothing has been covered yet
            covered_vocab = {p: m for p, m in covered_vocab.items() if m}
            if not covered_vocab:
                covered_vocab = None
            else:
                total = sum(len(m) for m in covered_vocab.values())
                print(f"  [RCM] covered vocab: {total} entries across {len(covered_vocab)} phases")
        else:
            covered_vocab = None
        common_kwargs["covered_vocab"] = covered_vocab

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
            narrative_frame=input,
            theme=config.lesson.theme,
            lesson_number=input.lesson_number,
        )
        return outline

    @staticmethod
    def _parse_outline(
        raw: dict,
        expected_blocks: int,
        narrative_frame: NarrativeFrame,
        theme: str = "",
        lesson_number: int = 0,
    ) -> CanonicalLessonPlan:
        
        grammar_ids = raw.get("grammar_ids", [])
        rationale = raw.get("rationale", "")
        blocks: List[CanonicalLessonBlock] = []
        for block_raw in raw.get("blocks", []):

            block_index = block_raw.get("block_index", 0)
            nb = narrative_frame.blocks[block_index - 1] if block_index - 1 < len(narrative_frame.blocks) else EmptyNarrativeBlock
            narrative = NarrativeBlock(
                narrative=block_raw.get("narrative_content", nb.narrative),
                alignment_notes=block_raw.get("alignment_notes_content", nb.alignment_notes),
                sentiment=block_raw.get("sentiment", nb.sentiment),
            )
            content_sequences = {}
            # using PHASE_PARSE_DETAILS
            for phase in Phase:
                if phase not in PHASE_PARSE_DETAILS:
                    continue
                items_raw = block_raw.get(PHASE_PARSE_DETAILS[phase]["field"], [])
                # vocab items has vocab and gloss 
                if PHASE_PARSE_DETAILS[phase]["is_vocab"]:
                    if isinstance(items_raw, dict):
                        content_sequences[phase] = [
                            CanonicalItem(text=vocab, gloss=gloss)
                            for vocab, gloss in items_raw.items()
                        ]
                    else:
                        content_sequences[phase] = [
                            CanonicalItem(text=item if isinstance(item, str) else item.get("text", str(item)),
                                          gloss=item.get("gloss", "") if isinstance(item, dict) else "")
                            for item in items_raw
                        ]
                else:
                    content_sequences[phase] = [
                        CanonicalItem(
                            text=item,
                            gloss="",
                        )
                        for item in items_raw
                    ]

                # Assign type and a stable id to every canonical item
                for item in content_sequences[phase]:
                    CanonicalItem.update_item(item, phase=phase)

            blocks.append(CanonicalLessonBlock(
                theme=theme,
                lesson_number=lesson_number,
                block_index=block_raw.get("block_index", len(blocks) + 1),
                grammar_ids=block_raw.get("grammar_ids", []),
                narrative=narrative,
                content_sequences=content_sequences,
            ))
        # Safety-net: ensure every block has at least one grammar_id.
        # The LLM sometimes leaves grammar_ids empty despite the prompt constraint;
        # fall back to the lesson-level grammar_ids so downstream steps always have
        # a grammar point to work with.
        for block in blocks:
            if not block.grammar_ids and grammar_ids:
                block.grammar_ids = grammar_ids[:1]

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
                    Phase.ADJECTIVES: [],
                    Phase.GRAMMAR: [],
                    Phase.NARRATIVE: [],
                },
                narrative=EmptyNarrativeBlock,
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
