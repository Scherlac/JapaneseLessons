from __future__ import annotations

from dataclasses import dataclass

from jlesson.models import GeneralItem, Phase
from .pipeline_core import ActionConfig, ActionStep, ItemBatch, LessonContext, StepAction


# ---------------------------------------------------------------------------
# Chunk type
# ---------------------------------------------------------------------------

@dataclass
class NounPracticeBatch(ItemBatch[GeneralItem]):
    """One LLM enrichment batch for nouns.

    Extends :class:`ItemBatch` with ``lesson_number`` so the action can pass it
    to the prompt builder without touching ``LessonContext`` or ``LessonConfig``.
    """

    lesson_number: int = 0


# ---------------------------------------------------------------------------
# Action
# ---------------------------------------------------------------------------

class NounPracticeAction(StepAction[NounPracticeBatch, list[GeneralItem]]):
    """Enrich one batch of nouns via a single LLM call.

    Input
    -----
    chunk : NounPracticeBatch
        A fixed-size slice of the full noun list plus the lesson ordinal.

    Output
    ------
    list[GeneralItem]
        Enriched items for this batch.  Items are paired with their source
        counterpart using ``zip`` (LLM responses shorter than the input batch
        yield a shorter output; merge_outputs handles the overall fallback).
    """

    def run(self, config: ActionConfig, chunk: NounPracticeBatch) -> list[GeneralItem]:
        prompt = config.language.prompts.build_noun_practice_prompt(
            chunk.items, chunk.lesson_number
        )
        result = config.runtime.call_llm(prompt)
        raw_items = result.get("noun_items", [])
        return [
            config.language.generator.convert_noun(raw, base)
            for raw, base in zip(raw_items, chunk.items)
        ]


# ---------------------------------------------------------------------------
# Step
# ---------------------------------------------------------------------------

class NounPracticeStep(ActionStep[NounPracticeBatch, list[GeneralItem]]):
    """Step 5 — LLM: enrich nouns with example sentences and memory tips.

    Inputs (from ``LessonContext``)
    --------------------------------
    nouns       list[GeneralItem]
        Selected lesson nouns to enrich.
    curriculum.lessons
        Used to derive the lesson ordinal for the prompt.
    config.num_nouns
        Used to assign ``block_index`` in ``merge_outputs``.

    Outputs
    -------
    noun_items  list[GeneralItem]
        Enriched nouns with example sentences and memory tips.
    """

    name = "noun_practice"
    description = "LLM: enrich nouns with examples + memory tips"
    BATCH_SIZE = 25

    @property
    def action(self) -> NounPracticeAction:
        return NounPracticeAction()

    def should_skip(self, ctx: LessonContext) -> bool:
        if ctx.noun_items:
            self._log(ctx, "       using retrieved noun items")
            return True
        return False

    def build_chunks(self, ctx: LessonContext) -> list[NounPracticeBatch]:
        lesson_number = len(ctx.curriculum.lessons) + 1
        items = list(ctx.nouns)
        return [
            NounPracticeBatch(
                batch_index=i,
                block_index=-1,
                items=items[start : start + self.BATCH_SIZE],
                lesson_number=lesson_number,
            )
            for i, start in enumerate(range(0, len(items), self.BATCH_SIZE))
        ] or [NounPracticeBatch(batch_index=0, block_index=-1, items=[], lesson_number=lesson_number)]

    def merge_outputs(
        self, ctx: LessonContext, outputs: list[list[GeneralItem]]
    ) -> LessonContext:
        noun_items_all = list(ctx.nouns)
        enriched = [item for batch_output in outputs for item in batch_output]
        ctx.noun_items = enriched if enriched else list(noun_items_all)
        for index, item in enumerate(ctx.noun_items):
            item.phase = Phase.NOUNS
            item.block_index = index // max(1, ctx.config.num_nouns) + 1
        self._log(ctx, f"       {len(ctx.noun_items)} noun items")
        src_lbl = ctx.language_config.source_label
        tgt_lbl = ctx.language_config.target_label
        ph_lbl = ctx.language_config.phonetic_label
        has_phonetic = bool(ph_lbl)
        ctx.report.add("vocabulary", self._vocab_table(ctx.noun_items, src_lbl, tgt_lbl, ph_lbl, has_phonetic))
        ctx.report.add("noun_practice", self._practice_section(ctx.noun_items, tgt_lbl, ph_lbl))
        return ctx

    @staticmethod
    def _vocab_table(items: list[GeneralItem], src_lbl: str, tgt_lbl: str, ph_lbl: str, has_phonetic: bool) -> str:
        header = f"| # | {src_lbl} | {tgt_lbl} |"
        sep = "|---|---------|----------|"
        if has_phonetic:
            header += f" {ph_lbl} |"
            sep += "--------|"
        lines = ["## Vocabulary", "", "### Nouns", ""]
        by_block: dict[int, list[GeneralItem]] = {}
        for item in items:
            by_block.setdefault(max(1, item.block_index), []).append(item)
        for block_index in sorted(by_block):
            if len(by_block) > 1:
                lines.extend([f"#### Block {block_index}", ""])
            lines.extend([header, sep])
            for index, item in enumerate(by_block[block_index], 1):
                row = f"| {index} | {item.source.display_text} | {item.target.display_text} |"
                if has_phonetic and item.target.pronunciation:
                    row += f" {item.target.pronunciation} |"
                lines.append(row)
            lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _practice_section(items: list[GeneralItem], tgt_lbl: str, ph_lbl: str) -> str:
        lines: list[str] = ["## Phase 1 - Noun Practice", ""]
        by_block: dict[int, list[GeneralItem]] = {}
        for item in items:
            by_block.setdefault(max(1, item.block_index), []).append(item)
        for block_index in sorted(by_block):
            if len(by_block) > 1:
                lines.extend([f"### Block {block_index}", ""])
            for index, item in enumerate(by_block[block_index], 1):
                lines.extend([f"#### {index}. {item.source.display_text}" if len(by_block) > 1 else f"### {index}. {item.source.display_text}", ""])
                lines.append(f"- **{tgt_lbl}:** {item.target.display_text}")
                if item.target.pronunciation:
                    lines.append(f"- **{ph_lbl}:** {item.target.pronunciation}")
                if item.target.extra.get("example_sentence_target"):
                    lines.append(f"- **Example:** {item.target.extra['example_sentence_target']}")
                if item.target.extra.get("example_sentence_source"):
                    lines.append(f"  *{item.target.extra['example_sentence_source']}*")
                if item.target.extra.get("memory_tip"):
                    lines.append(f"- **Memory tip:** {item.target.extra['memory_tip']}")
                lines.append("")
        return "\n".join(lines)