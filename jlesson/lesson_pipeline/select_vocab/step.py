from __future__ import annotations

from pathlib import Path

from jlesson.curriculum import suggest_new_vocab
from jlesson.models import NarrativeVocabBlock
from ..pipeline_core import LessonContext, PipelineStep
from ..runtime import PipelineRuntime
from .config import build_select_vocab_language_config


class SelectVocabStep(PipelineStep):
    """Step — Load vocab file and select fresh nouns/verbs.

    Selection is guided by the ``narrative_vocab_terms`` produced by
    ``ExtractNarrativeVocabStep``.  When narrative guidance is absent the step
    falls back to a curriculum-aware random draw via ``suggest_new_vocab``.

    Vocab loading is delegated to ``PipelineRuntime.load_vocab`` so the
    runtime can generate the file via LLM if it does not exist yet.
    """

    name = "select_vocab"
    description = "Pick fresh nouns/verbs from the vocab file"

    # Root of the jlesson package — used to resolve the vocab directory.
    _JLESSON_ROOT = Path(__file__).parent.parent.parent

    def execute(self, ctx: LessonContext) -> LessonContext:
        if ctx.nouns and ctx.verbs:
            self._log(ctx, "       using retrieved vocabulary")
            return ctx

        if not ctx.vocab:
            vocab_dir = self._JLESSON_ROOT / ctx.language_config.vocab_dir
            ctx.vocab = PipelineRuntime.load_vocab(ctx.config.theme, vocab_dir)

        step_config = build_select_vocab_language_config(ctx.language_config)
        prefix = step_config.verb_infinitive_prefix

        requested_nouns = ctx.config.num_nouns * ctx.config.lesson_blocks
        requested_verbs = ctx.config.num_verbs * ctx.config.lesson_blocks

        if ctx.narrative_vocab_terms:
            noun_terms = [block.nouns for block in ctx.narrative_vocab_terms]
            verb_terms = [block.verbs for block in ctx.narrative_vocab_terms]
            ctx.nouns = self._select_from_narrative(
                ctx.vocab["nouns"],
                covered_items=ctx.curriculum.covered_nouns,
                requested_per_block=ctx.config.num_nouns,
                lesson_blocks=ctx.config.lesson_blocks,
                terms_per_block=noun_terms,
                verb_infinitive_prefix="",  # nouns never have an infinitive prefix
            )
            ctx.verbs = self._select_from_narrative(
                ctx.vocab["verbs"],
                covered_items=ctx.curriculum.covered_verbs,
                requested_per_block=ctx.config.num_verbs,
                lesson_blocks=ctx.config.lesson_blocks,
                terms_per_block=verb_terms,
                verb_infinitive_prefix=prefix,
            )
        else:
            ctx.nouns, ctx.verbs = suggest_new_vocab(
                ctx.vocab["nouns"],
                ctx.vocab["verbs"],
                covered_nouns=ctx.curriculum.covered_nouns,
                covered_verbs=ctx.curriculum.covered_verbs,
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
        terms_per_block: list[list[str]],
        verb_infinitive_prefix: str,
    ) -> list[dict]:
        covered = {
            cls._normalize_term(item, prefix=verb_infinitive_prefix)
            for item in covered_items
        }
        fresh_items = [
            item for item in items
            if cls._normalize_term(item.get("id", ""), prefix=verb_infinitive_prefix) not in covered
        ]
        used: set[str] = set()
        selected: list[dict] = []
        for block_index in range(lesson_blocks):
            block_selected: list[dict] = []
            block_terms = terms_per_block[block_index] if block_index < len(terms_per_block) else []
            for term in block_terms:
                match = cls._find_match(fresh_items, used, term, prefix=verb_infinitive_prefix)
                if match is None:
                    match = cls._find_match(items, used, term, prefix=verb_infinitive_prefix)
                if match is None:
                    continue
                block_selected.append(match)
                used.add(cls._normalize_term(match.get("id", ""), prefix=verb_infinitive_prefix))
                if len(block_selected) >= requested_per_block:
                    break

            block_selected.extend(
                cls._fill_items(
                    fresh_items, used,
                    requested_per_block - len(block_selected),
                    prefix=verb_infinitive_prefix,
                )
            )
            if len(block_selected) < requested_per_block:
                block_selected.extend(
                    cls._fill_items(
                        items, used,
                        requested_per_block - len(block_selected),
                        prefix=verb_infinitive_prefix,
                    )
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
        prefix: str,
    ) -> list[dict]:
        picked: list[dict] = []
        for item in items:
            key = cls._normalize_term(item.get("id", ""), prefix=prefix)
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
        prefix: str,
    ) -> dict | None:
        normalized = cls._normalize_term(term, prefix=prefix)
        for item in items:
            candidate = cls._normalize_term(item.get("id", ""), prefix=prefix)
            if candidate == normalized and candidate not in used:
                return item
        return None

    @staticmethod
    def _normalize_term(term: str, *, prefix: str) -> str:
        normalized = (term or "").strip().lower()
        if prefix and normalized.startswith(prefix.lower()):
            normalized = normalized[len(prefix):]
        return normalized
