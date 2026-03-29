from __future__ import annotations

from pathlib import Path
from typing import Callable

from jlesson.models import GeneralItem, NarrativeVocabBlock, VocabItem
from jlesson.runtime import PipelineRuntime
from ..pipeline_core import LessonContext, PipelineStep
from .config import build_select_vocab_language_config
from .prompt import build_vocab_gap_fill_prompt


class SelectVocabStep(PipelineStep):
    """Step — Load vocab file and select fresh nouns/verbs.

    Selection is guided by the ``narrative_vocab_terms`` produced by
    ``ExtractNarrativeVocabStep``.  When narrative guidance is absent the step
    falls back to a curriculum-aware random draw via ``_select_fallback``.

    Vocab loading is delegated to ``PipelineRuntime.load_vocab`` so the
    runtime can generate the file via LLM if it does not exist yet.

    Outputs ``ctx.nouns`` and ``ctx.verbs`` as ``list[GeneralItem]`` — fully
    converted and ready for downstream LLM prompt builders.  No downstream
    step needs to call ``convert_raw_noun`` / ``convert_raw_verb`` on these
    fields any more.
    """

    name = "select_vocab"
    description = "Pick fresh nouns/verbs from the vocab file"

    # Root of the jlesson package — used to resolve the vocab directory.
    _JLESSON_ROOT = Path(__file__).parent.parent.parent

    def execute(self, ctx: LessonContext) -> LessonContext:
        if ctx.nouns and ctx.verbs:
            self._log(ctx, "       using retrieved vocabulary")
            return ctx

        if ctx.vocab is None:
            vocab_dir = self._JLESSON_ROOT / ctx.language_config.vocab_dir
            ctx.vocab = PipelineRuntime.load_vocab(ctx.config.theme, vocab_dir)

        step_config = build_select_vocab_language_config(ctx.language_config)
        prefix = step_config.verb_infinitive_prefix
        generator = ctx.language_config.generator

        requested_nouns = ctx.config.num_nouns * ctx.config.lesson_blocks
        requested_verbs = ctx.config.num_verbs * ctx.config.lesson_blocks

        if ctx.narrative_vocab_terms:
            noun_terms = [block.nouns for block in ctx.narrative_vocab_terms]
            verb_terms = [block.verbs for block in ctx.narrative_vocab_terms]
            ctx.nouns = self._select_from_narrative(
                ctx.vocab.nouns,
                covered_items=ctx.curriculum.covered_nouns,
                requested_per_block=ctx.config.num_nouns,
                lesson_blocks=ctx.config.lesson_blocks,
                terms_per_block=noun_terms,
                verb_infinitive_prefix="",
                generator_convert=generator.convert_raw_noun,
                item_type="nouns",
                ctx=ctx,
            )
            ctx.verbs = self._select_from_narrative(
                ctx.vocab.verbs,
                covered_items=ctx.curriculum.covered_verbs,
                requested_per_block=ctx.config.num_verbs,
                lesson_blocks=ctx.config.lesson_blocks,
                terms_per_block=verb_terms,
                verb_infinitive_prefix=prefix,
                generator_convert=generator.convert_raw_verb,
                item_type="verbs",
                ctx=ctx,
            )
        else:
            ctx.nouns, ctx.verbs = self._select_fallback(
                ctx.vocab.nouns,
                ctx.vocab.verbs,
                covered_nouns=ctx.curriculum.covered_nouns,
                covered_verbs=ctx.curriculum.covered_verbs,
                num_nouns=requested_nouns,
                num_verbs=requested_verbs,
                seed=ctx.config.seed,
                generator=generator,
            )

        self._log(ctx, f"       nouns : {[n.source.display_text for n in ctx.nouns]}")
        self._log(ctx, f"       verbs : {[v.source.display_text for v in ctx.verbs]}")
        return ctx

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
        ctx: LessonContext,
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

            # Gap-fill: ask the LLM to pick from the uncovered pool when file-based
            # matching alone cannot reach the quota.
            if gap > 0:
                llm_picked = cls._ask_llm_for_gap(
                    ctx,
                    fresh_items,
                    used=used,
                    prefix=verb_infinitive_prefix,
                    block_index=block_index,
                    item_type=item_type,
                    count=gap,
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
        ctx: LessonContext,
        items: list[VocabItem],
        *,
        used: set[str],
        prefix: str,
        block_index: int,
        item_type: str,
        count: int,
    ) -> list[VocabItem]:
        """Ask the LLM to select *count* items from the uncovered pool.

        Uses the narrative block text as context so the LLM can choose items
        that best fit the current story passage.  Falls back silently if the
        LLM call fails or the response is malformed.
        """
        available = [
            item for item in items
            if cls._normalize_term(item.id, prefix=prefix) not in used
        ]
        if not available or count <= 0:
            return []

        narrative_block = (
            ctx.narrative_blocks[block_index]
            if block_index < len(ctx.narrative_blocks)
            else ""
        )
        available_ids = [item.id for item in available]

        if item_type == "verbs":
            prompt = build_vocab_gap_fill_prompt(
                theme=ctx.config.theme,
                narrative_block=narrative_block,
                available_nouns=[],
                available_verbs=available_ids,
                target_nouns=0,
                target_verbs=count,
            )
        else:
            prompt = build_vocab_gap_fill_prompt(
                theme=ctx.config.theme,
                narrative_block=narrative_block,
                available_nouns=available_ids,
                available_verbs=[],
                target_nouns=count,
                target_verbs=0,
            )

        try:
            result = PipelineRuntime.ask_llm(ctx, prompt)
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
                id_map.pop(normalized)  # prevent duplicates
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
        """Select vocab not yet covered; fill from covered pool when exhausted.

        Returned items are fully converted ``GeneralItem`` objects ready for
        downstream prompt builders.  Pass ``seed`` for a reproducible shuffled
        draw; omit (or ``None``) for original list order.
        """
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
