from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from jlesson.models import GeneralItem, VocabFile, VocabItem

from ..pipeline_core import ActionConfig, NarrativeVocabPlan, SelectedVocabSet, StepAction
from .config import build_select_vocab_language_config
from .prompt import build_vocab_gap_fill_prompt


@dataclass
class SelectVocabRequest:
    """Composite request for vocab selection aligned to ``VocabFile``."""

    vocab: VocabFile | None
    vocab_dir: Path
    theme: str
    narrative_plan: NarrativeVocabPlan | None
    narrative_blocks: list[str]
    covered_nouns: list[str]
    covered_verbs: list[str]
    num_nouns_per_block: int
    num_verbs_per_block: int
    lesson_blocks: int
    seed: int | None


class SelectVocabAction(StepAction[SelectVocabRequest, SelectedVocabSet]):
    """Select fresh lesson vocab from a typed vocab source."""

    def run(self, config: ActionConfig, chunk: SelectVocabRequest) -> SelectedVocabSet:
        vocab = chunk.vocab
        if vocab is None:
            vocab = config.runtime.load_vocab(chunk.theme, chunk.vocab_dir)

        step_config = build_select_vocab_language_config(config.language)
        prefix = step_config.verb_infinitive_prefix
        generator = config.language.generator
        requested_nouns = chunk.num_nouns_per_block * chunk.lesson_blocks
        requested_verbs = chunk.num_verbs_per_block * chunk.lesson_blocks

        if chunk.narrative_plan and chunk.narrative_plan.blocks:
            noun_terms = [block.nouns for block in chunk.narrative_plan.blocks]
            verb_terms = [block.verbs for block in chunk.narrative_plan.blocks]
            nouns = self._select_from_narrative(
                vocab.nouns,
                covered_items=chunk.covered_nouns,
                requested_per_block=chunk.num_nouns_per_block,
                lesson_blocks=chunk.lesson_blocks,
                terms_per_block=noun_terms,
                verb_infinitive_prefix="",
                generator_convert=generator.convert_raw_noun,
                item_type="nouns",
                theme=chunk.theme,
                narrative_blocks=chunk.narrative_blocks,
                runtime=config.runtime,
            )
            verbs = self._select_from_narrative(
                vocab.verbs,
                covered_items=chunk.covered_verbs,
                requested_per_block=chunk.num_verbs_per_block,
                lesson_blocks=chunk.lesson_blocks,
                terms_per_block=verb_terms,
                verb_infinitive_prefix=prefix,
                generator_convert=generator.convert_raw_verb,
                item_type="verbs",
                theme=chunk.theme,
                narrative_blocks=chunk.narrative_blocks,
                runtime=config.runtime,
            )
        else:
            nouns, verbs = self._select_fallback(
                vocab.nouns,
                vocab.verbs,
                covered_nouns=chunk.covered_nouns,
                covered_verbs=chunk.covered_verbs,
                num_nouns=requested_nouns,
                num_verbs=requested_verbs,
                seed=chunk.seed,
                generator=generator,
            )

        return SelectedVocabSet(vocab=vocab, nouns=nouns, verbs=verbs)

    @classmethod
    def _select_from_narrative(
        cls,
        items: list[VocabItem],
        *,
        covered_items: list[str],
        requested_per_block: int,
        lesson_blocks: int,
        terms_per_block: list[list[str]],
        verb_infinitive_prefix: str,
        generator_convert: Callable[[dict], GeneralItem],
        item_type: str,
        theme: str,
        narrative_blocks: list[str],
        runtime,
    ) -> list[GeneralItem]:
        covered = {
            cls._normalize_term(item, prefix=verb_infinitive_prefix)
            for item in covered_items
        }
        fresh_items = [
            item for item in items
            if cls._normalize_term(item.id, prefix=verb_infinitive_prefix) not in covered
        ]
        used: set[str] = set()
        selected: list[VocabItem] = []
        for block_index in range(lesson_blocks):
            block_selected: list[VocabItem] = []
            block_terms = terms_per_block[block_index] if block_index < len(terms_per_block) else []
            for term in block_terms:
                match = cls._find_match(fresh_items, used, term, prefix=verb_infinitive_prefix)
                if match is None:
                    match = cls._find_match(items, used, term, prefix=verb_infinitive_prefix)
                if match is None:
                    continue
                block_selected.append(match)
                used.add(cls._normalize_term(match.id, prefix=verb_infinitive_prefix))
                if len(block_selected) >= requested_per_block:
                    break

            gap = requested_per_block - len(block_selected)
            if gap > 0:
                filled = cls._fill_items(fresh_items, used, gap, prefix=verb_infinitive_prefix)
                block_selected.extend(filled)
                gap = requested_per_block - len(block_selected)

            if gap > 0 and runtime is not None:
                llm_picked = cls._ask_llm_for_gap(
                    runtime,
                    fresh_items,
                    used=used,
                    prefix=verb_infinitive_prefix,
                    block_index=block_index,
                    item_type=item_type,
                    count=gap,
                    theme=theme,
                    narrative_blocks=narrative_blocks,
                )
                block_selected.extend(llm_picked)
                for item in llm_picked:
                    used.add(cls._normalize_term(item.id, prefix=verb_infinitive_prefix))
                gap = requested_per_block - len(block_selected)

            if gap > 0:
                block_selected.extend(
                    cls._fill_items(items, used, gap, prefix=verb_infinitive_prefix)
                )

            selected.extend(block_selected[:requested_per_block])

        return [generator_convert(item.model_dump()) for item in selected]

    @classmethod
    def _ask_llm_for_gap(
        cls,
        runtime,
        items: list[VocabItem],
        *,
        used: set[str],
        prefix: str,
        block_index: int,
        item_type: str,
        count: int,
        theme: str,
        narrative_blocks: list[str],
    ) -> list[VocabItem]:
        available = [
            item for item in items
            if cls._normalize_term(item.id, prefix=prefix) not in used
        ]
        if not available or count <= 0:
            return []

        narrative_block = narrative_blocks[block_index] if block_index < len(narrative_blocks) else ""
        available_ids = [item.id for item in available]

        if item_type == "verbs":
            prompt = build_vocab_gap_fill_prompt(
                theme=theme,
                narrative_block=narrative_block,
                available_nouns=[],
                available_verbs=available_ids,
                target_nouns=0,
                target_verbs=count,
            )
        else:
            prompt = build_vocab_gap_fill_prompt(
                theme=theme,
                narrative_block=narrative_block,
                available_nouns=available_ids,
                available_verbs=[],
                target_nouns=count,
                target_verbs=0,
            )

        try:
            result = runtime.call_llm(prompt)
            suggested_ids: list[str] = result.get(item_type) or []
        except Exception:
            return []

        id_map = {cls._normalize_term(item.id, prefix=prefix): item for item in available}
        picked: list[VocabItem] = []
        for sid in suggested_ids:
            normalized = cls._normalize_term(sid, prefix=prefix)
            item = id_map.get(normalized)
            if item is not None:
                picked.append(item)
                id_map.pop(normalized)
            if len(picked) >= count:
                break
        return picked

    @classmethod
    def _select_fallback(
        cls,
        all_nouns: list[VocabItem],
        all_verbs: list[VocabItem],
        *,
        covered_nouns: list[str],
        covered_verbs: list[str],
        num_nouns: int,
        num_verbs: int,
        seed: int | None,
        generator,
    ) -> tuple[list[GeneralItem], list[GeneralItem]]:
        import random

        covered_n = set(covered_nouns)
        covered_v = set(covered_verbs)

        fresh_nouns = [n for n in all_nouns if n.id not in covered_n]
        fresh_verbs = [v for v in all_verbs if v.id not in covered_v]

        if seed is not None:
            rng = random.Random(seed)
            rng.shuffle(fresh_nouns)
            rng.shuffle(fresh_verbs)

        selected_nouns = fresh_nouns[:num_nouns]
        if len(selected_nouns) < num_nouns:
            seen = {n.id for n in selected_nouns}
            gap = num_nouns - len(selected_nouns)
            selected_nouns += [n for n in all_nouns if n.id not in seen][:gap]

        selected_verbs = fresh_verbs[:num_verbs]
        if len(selected_verbs) < num_verbs:
            seen = {v.id for v in selected_verbs}
            gap = num_verbs - len(selected_verbs)
            selected_verbs += [v for v in all_verbs if v.id not in seen][:gap]

        return (
            [generator.convert_raw_noun(n.model_dump()) for n in selected_nouns[:num_nouns]],
            [generator.convert_raw_verb(v.model_dump()) for v in selected_verbs[:num_verbs]],
        )

    @classmethod
    def _fill_items(
        cls,
        items: list[VocabItem],
        used: set[str],
        count: int,
        *,
        prefix: str,
    ) -> list[VocabItem]:
        picked: list[VocabItem] = []
        for item in items:
            key = cls._normalize_term(item.id, prefix=prefix)
            if key in used:
                continue
            picked.append(item)
            used.add(key)
            if len(picked) >= count:
                break
        return picked

    @classmethod
    def _find_match(
        cls,
        items: list[VocabItem],
        used: set[str],
        term: str,
        *,
        prefix: str,
    ) -> VocabItem | None:
        normalized = cls._normalize_term(term, prefix=prefix)
        for item in items:
            candidate = cls._normalize_term(item.id, prefix=prefix)
            if candidate == normalized and candidate not in used:
                return item
        return None

    @staticmethod
    def _normalize_term(term: str, *, prefix: str) -> str:
        normalized = (term or "").strip().lower()
        if prefix and normalized.startswith(prefix.lower()):
            normalized = normalized[len(prefix):]
        return normalized