from __future__ import annotations

from jlesson.models import GeneralItem, Phase
from .pipeline_core import LessonContext, PipelineStep
from .pipeline_gadgets import PipelineGadgets


class VerbPracticeStep(PipelineStep):
    """Step 6 — LLM: enrich verbs with conjugation forms and memory tips."""

    name = "verb_practice"
    description = "LLM: enrich verbs with conjugations + memory tips"
    BATCH_SIZE = 20

    def execute(self, ctx: LessonContext) -> LessonContext:
        if ctx.verb_items:
            self._log(ctx, "       using retrieved verb items")
            return ctx
        lesson_number = len(ctx.curriculum.get("lessons", [])) + 1
        verb_items_all = [ctx.language_config.generator.convert_raw_verb(v) for v in ctx.verbs]
        raw_items: list[dict] = []
        for batch_start in range(0, len(verb_items_all), self.BATCH_SIZE):
            batch = verb_items_all[batch_start : batch_start + self.BATCH_SIZE]
            result = PipelineGadgets.ask_llm(
                ctx,
                ctx.language_config.prompts.build_verb_practice_prompt(batch, lesson_number),
            )
            raw_items.extend(result.get("verb_items", []))
        ctx.verb_items = []
        for verb_item, base_item in zip(raw_items, verb_items_all):
            ctx.verb_items.append(ctx.language_config.generator.convert_verb(verb_item, base_item))
        if not ctx.verb_items:
            ctx.verb_items = list(verb_items_all)
        for index, item in enumerate(ctx.verb_items):
            item.phase = Phase.VERBS
            item.block_index = index // max(1, ctx.config.num_verbs) + 1
        self._log(ctx, f"       {len(ctx.verb_items)} verb items")
        fm = ctx.language_config.field_map
        src_lbl, tgt_lbl, ph_lbl = fm.source_label, fm.target_label, fm.phonetic_label
        has_phonetic = bool(ph_lbl)
        has_masu = "masu_form" in ctx.language_config.field_map.target_special
        ctx.report.add("vocabulary", self._vocab_table(ctx.verb_items, src_lbl, tgt_lbl, ph_lbl, has_phonetic, has_masu))
        ctx.report.add("verb_practice", self._practice_section(ctx.verb_items, tgt_lbl, ph_lbl, has_masu))
        return ctx

    @staticmethod
    def _vocab_table(items: list[GeneralItem], src_lbl: str, tgt_lbl: str, ph_lbl: str, has_phonetic: bool, has_masu: bool) -> str:
        masu_lbl = "Polite form"
        header = f"| # | {src_lbl} | {tgt_lbl} |"
        sep = "|---|---------|----------|"
        if has_phonetic:
            header += f" {ph_lbl} |"
            sep += "--------|"
        if has_masu:
            header += f" {masu_lbl} |"
            sep += "-------------|"
        lines = ["### Verbs", ""]
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
                if has_masu and item.target.extra.get("masu_form"):
                    row += f" {item.target.extra['masu_form']} |"
                lines.append(row)
            lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _practice_section(items: list[GeneralItem], tgt_lbl: str, ph_lbl: str, has_masu: bool) -> str:
        lines: list[str] = ["## Phase 2 - Verb Practice", ""]
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
                if has_masu and item.target.extra.get("masu_form"):
                    lines.append(f"- **Polite form:** {item.target.extra['masu_form']}")
                polite = item.target.extra.get("polite_forms", {})
                if polite:
                    for form_name, form_value in polite.items():
                        lines.append(f"  - {form_name}: {form_value}")
                if item.target.extra.get("example_sentence_target"):
                    lines.append(f"- **Example:** {item.target.extra['example_sentence_target']}")
                if item.target.extra.get("example_sentence_source"):
                    lines.append(f"  *{item.target.extra['example_sentence_source']}*")
                if item.target.extra.get("memory_tip"):
                    lines.append(f"- **Memory tip:** {item.target.extra['memory_tip']}")
                lines.append("")
        return "\n".join(lines)