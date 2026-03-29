from __future__ import annotations

from pathlib import Path

from jlesson.curriculum import suggest_new_vocab
from .pipeline_core import LessonContext, PipelineStep
from .pipeline_gadgets import PipelineGadgets


class SelectVocabStep(PipelineStep):
    """Step 1 — Load vocab file and select fresh nouns/verbs."""

    name = "select_vocab"
    description = "Pick fresh nouns/verbs from the vocab file"

    def execute(self, ctx: LessonContext) -> LessonContext:
        if ctx.nouns and ctx.verbs:
            self._log(ctx, "       using retrieved vocabulary")
            return ctx
        vocab_dir = Path(__file__).parent.parent / ctx.language_config.vocab_dir
        if not ctx.vocab:
            ctx.vocab = PipelineGadgets.load_vocab(ctx.config.theme, vocab_dir)
        requested_nouns = ctx.config.num_nouns * ctx.config.lesson_blocks
        requested_verbs = ctx.config.num_verbs * ctx.config.lesson_blocks
        if ctx.narrative_vocab_terms:
            ctx.nouns = self._select_from_narrative(
                ctx.vocab["nouns"],
                covered_items=ctx.curriculum.get("covered_nouns", []),
                requested_per_block=ctx.config.num_nouns,
                lesson_blocks=ctx.config.lesson_blocks,
                narrative_blocks=ctx.narrative_vocab_terms,
                term_key="nouns",
                is_verb=False,
            )
            ctx.verbs = self._select_from_narrative(
                ctx.vocab["verbs"],
                covered_items=ctx.curriculum.get("covered_verbs", []),
                requested_per_block=ctx.config.num_verbs,
                lesson_blocks=ctx.config.lesson_blocks,
                narrative_blocks=ctx.narrative_vocab_terms,
                term_key="verbs",
                is_verb=True,
            )
        else:
            ctx.nouns, ctx.verbs = suggest_new_vocab(
                ctx.vocab["nouns"],
                ctx.vocab["verbs"],
                covered_nouns=ctx.curriculum.get("covered_nouns", []),
                covered_verbs=ctx.curriculum.get("covered_verbs", []),
                num_nouns=requested_nouns,
                num_verbs=requested_verbs,
                seed=ctx.config.seed,
            )
        self._log(ctx, f"       nouns : {[n['source'] for n in ctx.nouns]}")
        self._log(ctx, f"       verbs : {[v['source'] for v in ctx.verbs]}")
        return ctx

    @classmethod
    def _select_from_narrative(
        cls,
        items: list[dict],
        *,
        covered_items: list[str],
        requested_per_block: int,
        lesson_blocks: int,
        narrative_blocks: list[dict[str, list[str]]],
        term_key: str,
        is_verb: bool,
    ) -> list[dict]:
        covered = {cls._normalize_term(item, is_verb=is_verb) for item in covered_items}
        fresh_items = [
            item for item in items
            if cls._normalize_term(item.get("id", ""), is_verb=is_verb) not in covered
        ]
        used: set[str] = set()
        selected: list[dict] = []
        for block_index in range(lesson_blocks):
            block_selected: list[dict] = []
            block_terms = []
            if block_index < len(narrative_blocks):
                block_terms = narrative_blocks[block_index].get(term_key, [])
            for term in block_terms:
                match = cls._find_match(fresh_items, used, term, is_verb=is_verb)
                if match is None:
                    match = cls._find_match(items, used, term, is_verb=is_verb)
                if match is None:
                    continue
                block_selected.append(match)
                used.add(cls._normalize_term(match.get("id", ""), is_verb=is_verb))
                if len(block_selected) >= requested_per_block:
                    break

            block_selected.extend(
                cls._fill_items(fresh_items, used, requested_per_block - len(block_selected), is_verb=is_verb)
            )
            if len(block_selected) < requested_per_block:
                block_selected.extend(
                    cls._fill_items(items, used, requested_per_block - len(block_selected), is_verb=is_verb)
                )
            selected.extend(block_selected[:requested_per_block])
        return selected

    @classmethod
    def _fill_items(
        cls,
        items: list[dict],
        used: set[str],
        count: int,
        *,
        is_verb: bool,
    ) -> list[dict]:
        picked: list[dict] = []
        for item in items:
            key = cls._normalize_term(item.get("id", ""), is_verb=is_verb)
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
        items: list[dict],
        used: set[str],
        term: str,
        *,
        is_verb: bool,
    ) -> dict | None:
        normalized = cls._normalize_term(term, is_verb=is_verb)
        for item in items:
            candidate = cls._normalize_term(item.get("id", ""), is_verb=is_verb)
            if candidate == normalized and candidate not in used:
                return item
        return None

    @staticmethod
    def _normalize_term(term: str, *, is_verb: bool) -> str:
        normalized = (term or "").strip().lower()
        if is_verb and normalized.startswith("to "):
            normalized = normalized[3:]
        return normalized
