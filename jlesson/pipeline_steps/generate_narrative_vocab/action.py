"""Stateless narrative vocabulary generation action.

This module contains the pure transformation logic extracted from
``GenerateNarrativeVocabStep.execute``.  It has no knowledge of
``LessonContext`` and performs all I/O through ``config.runtime``.
"""
from __future__ import annotations

from jlesson.models import VocabFile, VocabItem
from jlesson.vocab_generator import normalize_vocab_item

from ..pipeline_core import ActionConfig, NarrativeVocabPlan, StepAction

_BATCH_SIZE = 60


class GenerateNarrativeVocabAction(StepAction[NarrativeVocabPlan, VocabFile]):
    """Generate full vocab entries for terms extracted from the narrative.

    Input
    -----
    chunk : NarrativeVocabPlan
        The typed output of ``ExtractNarrativeVocabStep`` — per-block noun/verb
        term lists.  Using ``NarrativeVocabPlan`` as the chunk type makes the
        inter-step dependency explicit: this action directly consumes the
        artifact the preceding step produces.

    Output
    ------
    VocabFile
        Full vocab entries (with target-language forms) built from the term
        lists.  One LLM call is made per batch via ``config.runtime.call_llm``.
    """

    def run(self, config: ActionConfig, chunk: NarrativeVocabPlan) -> VocabFile:
        all_nouns: list[str] = []
        all_verbs: list[str] = []
        seen_nouns: set[str] = set()
        seen_verbs: set[str] = set()
        for block in chunk.blocks:
            for term in block.nouns:
                key = term.lower()
                if key not in seen_nouns:
                    all_nouns.append(term)
                    seen_nouns.add(key)
            for term in block.verbs:
                key = term.lower()
                if key not in seen_verbs:
                    all_verbs.append(term)
                    seen_verbs.add(key)

        lc = config.language
        nouns: list[dict] = []
        verbs: list[dict] = []

        max_batches = max(
            (len(all_nouns) + _BATCH_SIZE - 1) // _BATCH_SIZE,
            (len(all_verbs) + _BATCH_SIZE - 1) // _BATCH_SIZE,
            1,
        )
        for i in range(max_batches):
            noun_batch = all_nouns[i * _BATCH_SIZE : (i + 1) * _BATCH_SIZE]
            verb_batch = all_verbs[i * _BATCH_SIZE : (i + 1) * _BATCH_SIZE]
            prompt = lc.prompts.build_narrative_vocab_generate_prompt(
                nouns=noun_batch,
                verbs=verb_batch,
                theme=config.lesson.theme,
            )
            result = config.runtime.call_llm(prompt)
            nouns.extend(
                normalize_vocab_item(n, lc)
                for n in result.get("nouns", [])
                if isinstance(n, dict)
                and n.get(lc.source.vocab_source_key)
                and n.get(lc.target.vocab_source_key)
            )
            verbs.extend(
                normalize_vocab_item(v, lc)
                for v in result.get("verbs", [])
                if isinstance(v, dict)
                and v.get(lc.source.vocab_source_key)
                and v.get(lc.target.vocab_source_key)
            )

        return VocabFile(
            theme=config.lesson.theme,
            nouns=[VocabItem.model_validate(n) for n in nouns],
            verbs=[VocabItem.model_validate(v) for v in verbs],
        )
