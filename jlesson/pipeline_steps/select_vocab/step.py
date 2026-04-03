from __future__ import annotations

from pathlib import Path
from typing import Callable

from jlesson.models import GeneralItem, VocabItem
from jlesson.runtime import PipelineRuntime

from ..pipeline_core import ActionStep, LessonContext, SelectedVocabSet
from .action import SelectVocabAction, SelectVocabRequest


class SelectVocabStep(ActionStep[SelectVocabRequest, SelectedVocabSet]):
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
    _action = SelectVocabAction()

    class _LegacyRuntimeAdapter:
        def __init__(self, ctx: LessonContext) -> None:
            self._ctx = ctx

        def call_llm(self, prompt: str) -> dict:
            return PipelineRuntime.ask_llm(self._ctx, prompt)

    # Root of the jlesson package — used to resolve the vocab directory.
    _JLESSON_ROOT = Path(__file__).parent.parent.parent

    @property
    def action(self) -> SelectVocabAction:
        return self._action

    def should_skip(self, ctx: LessonContext) -> bool:
        if ctx.nouns and ctx.verbs:
            self._log(ctx, "       using retrieved vocabulary")
            return True
        return False

    def build_chunks(self, ctx: LessonContext) -> list[SelectVocabRequest]:
        vocab_dir = self._JLESSON_ROOT / ctx.language_config.vocab_dir
        return [
            SelectVocabRequest(
                vocab=ctx.vocab,
                vocab_dir=vocab_dir,
                theme=ctx.config.theme,
                canonical_selection=ctx.canonical_vocab,
                narrative_blocks=list(ctx.narrative_blocks),
                covered_nouns=list(ctx.curriculum.covered_nouns),
                covered_verbs=list(ctx.curriculum.covered_verbs),
                num_nouns_per_block=ctx.config.num_nouns,
                num_verbs_per_block=ctx.config.num_verbs,
                lesson_blocks=ctx.config.lesson_blocks,
                seed=ctx.config.seed,
            )
        ]

    def merge_outputs(self, ctx: LessonContext, outputs: list[SelectedVocabSet]) -> LessonContext:
        result = outputs[-1]
        ctx.vocab = result.vocab
        ctx.nouns = result.nouns
        ctx.verbs = result.verbs
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
        return SelectVocabAction._select_from_narrative(
            items,
            covered_items=covered_items,
            requested_per_block=requested_per_block,
            lesson_blocks=lesson_blocks,
            terms_per_block=terms_per_block,
            verb_infinitive_prefix=verb_infinitive_prefix,
            generator_convert=generator_convert,
            item_type=item_type,
            theme=ctx.config.theme,
            narrative_blocks=ctx.narrative_blocks,
            runtime=cls._LegacyRuntimeAdapter(ctx),
        )

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
        return SelectVocabAction._ask_llm_for_gap(
            cls._LegacyRuntimeAdapter(ctx),
            items,
            used=used,
            prefix=prefix,
            block_index=block_index,
            item_type=item_type,
            count=count,
            theme=ctx.config.theme,
            narrative_blocks=ctx.narrative_blocks,
        )

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
        return SelectVocabAction._select_fallback(
            all_nouns,
            all_verbs,
            covered_nouns=covered_nouns,
            covered_verbs=covered_verbs,
            num_nouns=num_nouns,
            num_verbs=num_verbs,
            seed=seed,
            generator=generator,
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
        return SelectVocabAction._fill_items(items, used, count, prefix=prefix)

    @classmethod
    def _find_match(
        cls,
        items: list[VocabItem],
        used: set[str],
        term: str,
        *,
        prefix: str,
    ) -> VocabItem | None:
        return SelectVocabAction._find_match(items, used, term, prefix=prefix)

    @staticmethod
    def _normalize_term(term: str, *, prefix: str) -> str:
        return SelectVocabAction._normalize_term(term, prefix=prefix)
