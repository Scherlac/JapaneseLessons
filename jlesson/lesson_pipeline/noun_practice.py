from __future__ import annotations

from jlesson.models import GeneralItem, Phase
from .pipeline_core import LessonContext, PipelineStep
from .pipeline_llm import ask_llm


class NounPracticeStep(PipelineStep):
    """Step 5 — LLM: enrich nouns with example sentences and memory tips."""

    name = "noun_practice"
    description = "LLM: enrich nouns with examples + memory tips"

    def execute(self, ctx: LessonContext) -> LessonContext:
        if ctx.noun_items:
            self._log(ctx, "       using retrieved noun items")
            return ctx
        lesson_number = len(ctx.curriculum.get("lessons", [])) + 1
        noun_items = [ctx.language_config.generator.convert_raw_noun(n) for n in ctx.nouns]
        result = ask_llm(
            ctx,
            ctx.language_config.prompts.build_noun_practice_prompt(noun_items, lesson_number),
        )
        raw_items = result.get("noun_items", [])
        ctx.noun_items = []
        for noun_item in raw_items:
            source_item = next((n for n in ctx.nouns if n["english"] == noun_item["english"]), None)
            if source_item:
                ctx.noun_items.append(ctx.language_config.generator.convert_noun(noun_item, source_item))
            else:
                ctx.noun_items.append(ctx.language_config.generator.convert_noun(noun_item, {}))
        if not ctx.noun_items:
            for noun_source in ctx.nouns:
                ctx.noun_items.append(ctx.language_config.generator.convert_raw_noun(noun_source))
        for index, item in enumerate(ctx.noun_items):
            item.phase = Phase.NOUNS
            item.block_index = index // max(1, ctx.config.num_nouns) + 1
        self._log(ctx, f"       {len(ctx.noun_items)} noun items")
        if ctx.language_config.code == "hun-eng":
            src_lbl, tgt_lbl, ph_lbl, has_phonetic = "Magyar", "English", "Pronunciation", True
        else:
            src_lbl, tgt_lbl, ph_lbl, has_phonetic = "English", "Japanese", "Romaji", True
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