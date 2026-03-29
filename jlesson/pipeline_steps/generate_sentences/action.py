"""Stateless sentence generation action for one lesson block.

This module contains the pure transformation logic extracted from
``NarrativeGrammarStep.execute``.  It has no knowledge of ``LessonContext``
and performs all I/O through ``config.runtime`` (a ``RuntimeServices`` instance),
making it independently testable with a mock runtime.
"""
from __future__ import annotations

from jlesson.models import GrammarItem, Phase, Sentence
from ..pipeline_core import ActionConfig, BlockChunk, StepAction
from .config import build_narrative_grammar_language_config
from .prompt import build_grammar_sentences_prompt


class GenerateSentencesAction(StepAction[BlockChunk, list[Sentence]]):
    """Generate grammar-practice sentences for one lesson block.

    Input
    -----
    chunk : BlockChunk
        Narrative passage, noun/verb slices, and grammar points for the block.

    Output
    ------
    list[Sentence]
        Grammar-practice sentences with ``block_index`` and ``phase`` set.
        One LLM call is made via ``config.runtime.call_llm``.

    All prompt construction is delegated to :func:`.prompt.build_grammar_sentences_prompt`.
    Language-specific field names are resolved from ``config.language`` via
    :func:`.config.build_narrative_grammar_language_config`.
    """

    def run(self, config: ActionConfig, chunk: BlockChunk) -> list[Sentence]:
        step_config = build_narrative_grammar_language_config(config.language)
        persons = list(step_config.persons)

        prompt = build_grammar_sentences_prompt(
            list(chunk.grammar),
            list(chunk.nouns),
            list(chunk.verbs),
            persons=persons,
            sentences_per_grammar=config.lesson.sentences_per_grammar,
            narrative=chunk.narrative,
            teacher_description=step_config.teacher_description,
            output_source_field=step_config.output_source_field,
            output_target_field=step_config.output_target_field,
            output_phonetic_field=step_config.output_phonetic_field,
        )

        result = config.runtime.call_llm(prompt)

        sentences: list[Sentence] = []
        for sentence_source in result.get("sentences", []):
            sentence = config.language.generator.convert_sentence(sentence_source)
            sentence.block_index = config.block_index + 1
            sentence.phase = Phase.GRAMMAR
            sentences.append(sentence)
        return sentences
