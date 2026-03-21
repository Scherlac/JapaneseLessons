from __future__ import annotations

from jlesson.models import GeneralItem

from .runtime import lesson_pipeline_module


class VerbPracticeStep(lesson_pipeline_module().PipelineStep):
    """Step 6 — LLM: enrich verbs with conjugation forms and memory tips."""

    name = "verb_practice"
    description = "LLM: enrich verbs with conjugations + memory tips"

    def execute(self, ctx: lesson_pipeline_module().LessonContext) -> lesson_pipeline_module().LessonContext:
        if ctx.verb_items:
            self._log(ctx, "       using retrieved verb items")
            return ctx
        lesson_number = len(ctx.curriculum.get("lessons", [])) + 1
        verb_items = [ctx.language_config.generator.convert_raw_verb(v) for v in ctx.verbs]
        result = lesson_pipeline_module().PipelineGadgets.ask_llm(
            ctx,
            ctx.language_config.prompts.build_verb_practice_prompt(verb_items, lesson_number),
        )
        raw_items = result.get("verb_items", [])
        ctx.verb_items = []
        for verb_item in raw_items:
            source_item = next((v for v in ctx.verbs if v["english"] == verb_item["english"]), None)
            if source_item:
                ctx.verb_items.append(ctx.language_config.generator.convert_verb(verb_item, source_item))
            else:
                ctx.verb_items.append(ctx.language_config.generator.convert_verb(verb_item, {}))
        if not ctx.verb_items:
            for verb_source in ctx.verbs:
                ctx.verb_items.append(ctx.language_config.generator.convert_raw_verb(verb_source))
        for item in ctx.verb_items:
            item.item_type = "verb"
        self._log(ctx, f"       {len(ctx.verb_items)} verb items")
        if ctx.language_config.code == "hun-eng":
            src_lbl, tgt_lbl, ph_lbl, has_phonetic, has_masu = "Magyar", "English", "Pronunciation", True, False
        else:
            src_lbl, tgt_lbl, ph_lbl, has_phonetic, has_masu = "English", "Japanese", "Romaji", True, True
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
        lines = ["### Verbs", "", header, sep]
        for index, item in enumerate(items, 1):
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
        for index, item in enumerate(items, 1):
            lines.extend([f"### {index}. {item.source.display_text}", ""])
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