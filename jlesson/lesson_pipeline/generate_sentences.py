from __future__ import annotations

from jlesson.models import Sentence
from jlesson.pipeline_core import LessonContext, PipelineStep
from jlesson.pipeline_gadgets import PipelineGadgets


class GenerateSentencesStep(PipelineStep):
    """Step 3 — LLM: generate practice sentences."""

    name = "generate_sentences"
    description = "LLM: produce practice sentences"

    def execute(self, ctx: LessonContext) -> LessonContext:
        if ctx.sentences:
            self._log(ctx, "       using retrieved sentences")
            return ctx
        noun_items = [ctx.language_config.generator.convert_raw_noun(n) for n in ctx.nouns]
        verb_items = [ctx.language_config.generator.convert_raw_verb(v) for v in ctx.verbs]
        lesson_number = len(ctx.curriculum.get("lessons", [])) + 1
        narrative = (ctx.config.narrative or "").strip()
        if not narrative:
            narrative = ctx.language_config.generator.build_default_narrative(
                theme=ctx.config.theme,
                lesson_number=lesson_number,
            )
        prompt = ctx.language_config.prompts.build_grammar_generate_prompt(
            PipelineGadgets.coerce_grammar_items(ctx.selected_grammar),
            noun_items,
            verb_items,
            sentences_per_grammar=ctx.config.sentences_per_grammar,
            narrative=narrative,
        )
        result = PipelineGadgets.ask_llm(ctx, prompt)
        sentences = result.get("sentences", [])
        ctx.sentences = []
        for sentence_source in sentences:
            ctx.sentences.append(ctx.language_config.generator.convert_sentence(sentence_source))
        self._log(ctx, f"       {len(ctx.sentences)} sentences")
        if narrative:
            self._log(ctx, f"       narrative : {narrative[:96]}{'...' if len(narrative) > 96 else ''}")
            ctx.report.add(
                "grammar_context",
                "\n".join(
                    [
                        "## Narrative Context",
                        "",
                        narrative,
                        "",
                    ]
                ),
            )
        if ctx.sentences:
            if ctx.language_config.code == "hun-eng":
                src_lbl, tgt_lbl, ph_lbl, has_phonetic = "Magyar", "English", "Pronunciation", True
            else:
                src_lbl, tgt_lbl, ph_lbl, has_phonetic = "English", "Japanese", "Romaji", True
            ctx.report.add(
                "grammar_practice",
                self._grammar_section(ctx.sentences, src_lbl, tgt_lbl, ph_lbl, has_phonetic),
            )
        return ctx

    @staticmethod
    def _grammar_section(sentences: list[Sentence], src_lbl: str, tgt_lbl: str, ph_lbl: str, has_phonetic: bool) -> str:
        header = f"| # | Person | {src_lbl} | {tgt_lbl} |"
        sep = "|---|--------|---------|----------|"
        if has_phonetic:
            header += f" {ph_lbl} |"
            sep += "--------|"
        lines: list[str] = ["## Phase 3 - Grammar Practice", ""]
        by_grammar: dict[str, list[Sentence]] = {}
        for sentence in sentences:
            by_grammar.setdefault(sentence.grammar_id, []).append(sentence)
        for grammar_id, grammar_sentences in by_grammar.items():
            lines.extend([f"### {grammar_id}", "", header, sep])
            for index, sentence in enumerate(grammar_sentences, 1):
                row = (
                    f"| {index} | {sentence.grammar_parameters.get('person', '')} | {sentence.source.display_text} | {sentence.target.display_text} |"
                )
                if has_phonetic and sentence.target.pronunciation:
                    row += f" {sentence.target.pronunciation} |"
                lines.append(row)
            lines.append("")
        return "\n".join(lines)