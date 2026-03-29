from __future__ import annotations

from jlesson.models import Phase, Sentence
from .pipeline_core import LessonContext, PipelineStep
from .pipeline_gadgets import PipelineGadgets


class NarrativeGrammarStep(PipelineStep):
    """Generate block-aware grammar sentences aligned to the narrative progression."""

    name = "narrative_grammar"
    description = "LLM: generate grammar sentences for each narrative block"

    def execute(self, ctx: LessonContext) -> LessonContext:
        if ctx.sentences:
            self._log(ctx, "       using retrieved sentences")
            return ctx
        ctx.sentences = []
        noun_blocks = self._chunk(ctx.nouns, ctx.config.num_nouns)
        verb_blocks = self._chunk(ctx.verbs, ctx.config.num_verbs)
        total_blocks = max(
            len(noun_blocks),
            len(verb_blocks),
            len(ctx.narrative_blocks),
            ctx.config.lesson_blocks,
        )
        for block_index in range(total_blocks):
            block_nouns = noun_blocks[block_index] if block_index < len(noun_blocks) else []
            block_verbs = verb_blocks[block_index] if block_index < len(verb_blocks) else []
            noun_items = [ctx.language_config.generator.convert_raw_noun(n) for n in block_nouns]
            verb_items = [ctx.language_config.generator.convert_raw_verb(v) for v in block_verbs]
            block_narrative = ctx.narrative_blocks[block_index] if block_index < len(ctx.narrative_blocks) else ""
            block_grammar = (
                ctx.selected_grammar_blocks[block_index]
                if block_index < len(ctx.selected_grammar_blocks) and ctx.selected_grammar_blocks[block_index]
                else ctx.selected_grammar
            )
            prompt = ctx.language_config.prompts.build_grammar_generate_prompt(
                block_grammar,
                noun_items,
                verb_items,
                sentences_per_grammar=ctx.config.sentences_per_grammar,
                narrative=block_narrative,
            )
            result = PipelineGadgets.ask_llm(ctx, prompt)
            for sentence_source in result.get("sentences", []):
                sentence = ctx.language_config.generator.convert_sentence(sentence_source)
                sentence.block_index = block_index + 1
                sentence.phase = Phase.GRAMMAR
                ctx.sentences.append(sentence)
        self._log(ctx, f"       {len(ctx.sentences)} sentences")
        if ctx.sentences:
            src_lbl = ctx.language_config.source_label
            tgt_lbl = ctx.language_config.target_label
            ph_lbl = ctx.language_config.phonetic_label
            has_phonetic = bool(ctx.language_config.phonetic_label)
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
        by_block: dict[int, list[Sentence]] = {}
        for sentence in sentences:
            by_block.setdefault(max(1, sentence.block_index), []).append(sentence)
        for block_index in sorted(by_block):
            block_sentences = by_block[block_index]
            if len(by_block) > 1:
                lines.extend([f"### Block {block_index}", ""])
            by_grammar: dict[str, list[Sentence]] = {}
            for sentence in block_sentences:
                by_grammar.setdefault(sentence.grammar_id, []).append(sentence)
            for grammar_id, grammar_sentences in by_grammar.items():
                lines.extend([f"#### {grammar_id}" if len(by_block) > 1 else f"### {grammar_id}", "", header, sep])
                for index, sentence in enumerate(grammar_sentences, 1):
                    row = (
                        f"| {index} | {sentence.grammar_parameters.get('person', '')} | {sentence.source.display_text} | {sentence.target.display_text} |"
                    )
                    if has_phonetic and sentence.target.pronunciation:
                        row += f" {sentence.target.pronunciation} |"
                    lines.append(row)
                lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _chunk(items: list[dict], size: int) -> list[list[dict]]:
        if size <= 0:
            return [items] if items else []
        return [items[index:index + size] for index in range(0, len(items), size)]


GenerateSentencesStep = NarrativeGrammarStep