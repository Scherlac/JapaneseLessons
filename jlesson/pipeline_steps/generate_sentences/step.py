from __future__ import annotations

from jlesson.models import GeneralItem, GrammarItem, Sentence
from ..pipeline_core import ActionStep, BlockChunk, LessonContext
from .action import GenerateSentencesAction


class NarrativeGrammarStep(ActionStep[BlockChunk, list[Sentence]]):
    """Generate block-aware grammar sentences aligned to the narrative progression.

    Inputs (from ``LessonContext``)
    --------------------------------
    nouns                   list[GeneralItem]
        Lesson nouns, chunked into blocks of ``config.num_nouns`` per block.
    verbs                   list[GeneralItem]
        Lesson verbs, chunked into blocks of ``config.num_verbs`` per block.
    narrative_blocks        list[str]
        One story passage per block (may be empty).
    selected_grammar_blocks list[list[GrammarItem]]
        Per-block grammar selection produced by ``GrammarSelectStep``.
    selected_grammar        list[GrammarItem]
        Flat grammar list used as a fallback when per-block selection is absent.
    config.num_nouns / num_verbs / sentences_per_grammar / lesson_blocks
        Sizing parameters.

    Outputs
    -------
    sentences   list[Sentence]
        Grammar practice sentences with ``block_index`` and ``phase`` set.

    Implementation
    --------------
    The iteration loop (one ``BlockChunk`` per lesson block) is handled by the
    inherited ``ActionStep.execute``.  The step only declares the chunk shape
    (``build_chunks``) and how to write results back to context
    (``merge_outputs``).  The actual LLM call lives in ``GenerateSentencesAction``.
    """

    name = "narrative_grammar"
    description = "LLM: generate grammar sentences for each narrative block"

    @property
    def action(self) -> GenerateSentencesAction:
        return GenerateSentencesAction()

    def should_skip(self, ctx: LessonContext) -> bool:
        if ctx.sentences:
            self._log(ctx, "       using retrieved sentences")
            return True
        return False

    def build_chunks(self, ctx: LessonContext) -> list[BlockChunk]:
        noun_blocks = self._chunk(ctx.nouns, ctx.config.num_nouns)
        verb_blocks = self._chunk(ctx.verbs, ctx.config.num_verbs)
        total_blocks = max(
            len(noun_blocks),
            len(verb_blocks),
            len(ctx.narrative_blocks),
            ctx.config.lesson_blocks,
        )
        chunks: list[BlockChunk] = []
        for block_index in range(total_blocks):
            block_grammar: list[GrammarItem] = (
                ctx.selected_grammar_blocks[block_index]
                if block_index < len(ctx.selected_grammar_blocks)
                and ctx.selected_grammar_blocks[block_index]
                else ctx.selected_grammar
            )
            chunks.append(BlockChunk(
                block_index=block_index,
                narrative=(
                    ctx.narrative_blocks[block_index]
                    if block_index < len(ctx.narrative_blocks)
                    else ""
                ),
                nouns=noun_blocks[block_index] if block_index < len(noun_blocks) else [],
                verbs=verb_blocks[block_index] if block_index < len(verb_blocks) else [],
                grammar=block_grammar,
            ))
        return chunks

    def merge_outputs(
        self, ctx: LessonContext, outputs: list[list[Sentence]]
    ) -> LessonContext:
        ctx.generated_sentence_blocks = outputs
        ctx.review_results = []
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
    def _grammar_section(
        sentences: list[Sentence],
        src_lbl: str,
        tgt_lbl: str,
        ph_lbl: str,
        has_phonetic: bool,
    ) -> str:
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
                lines.extend(
                    [
                        f"#### {grammar_id}" if len(by_block) > 1 else f"### {grammar_id}",
                        "",
                        header,
                        sep,
                    ]
                )
                for index, sentence in enumerate(grammar_sentences, 1):
                    row = (
                        f"| {index} | {sentence.grammar_parameters.get('person', '')} "
                        f"| {sentence.source.display_text} | {sentence.target.display_text} |"
                    )
                    if has_phonetic and sentence.target.pronunciation:
                        row += f" {sentence.target.pronunciation} |"
                    lines.append(row)
                lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _chunk(items: list[GeneralItem], size: int) -> list[list[GeneralItem]]:
        if size <= 0:
            return [items] if items else []
        return [items[index : index + size] for index in range(0, len(items), size)]

