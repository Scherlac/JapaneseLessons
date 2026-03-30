"""Stateless narrative generation action.

This module contains the pure transformation logic extracted from
``NarrativeGeneratorStep.execute``.  It has no knowledge of ``LessonContext``
and performs all I/O through ``config.runtime``, making it independently
testable with a mock runtime.
"""
from __future__ import annotations

from ..pipeline_core import ActionConfig, NarrativeFrame, NarrativeGenChunk, StepAction
from .config import build_narrative_generator_language_config
from .prompt import build_narrative_generator_prompt


class NarrativeGeneratorAction(StepAction[NarrativeGenChunk, NarrativeFrame]):
    """Generate or pass through a narrative progression across lesson blocks.

    Input
    -----
    chunk : NarrativeGenChunk
        Theme, lesson number, desired block count, and any user-provided seed
        passages.  If ``chunk.seed_blocks`` already covers all blocks, the
        action returns them directly without an LLM call.

    Output
    ------
    NarrativeFrame
        Typed container of ``chunk.lesson_blocks`` narrative passages.

    One LLM call is made via ``config.runtime.call_llm`` when the seed blocks
    are insufficient.  If the LLM returns fewer blocks than requested, the
    language-specific default builder fills the remainder.
    """

    def run(self, config: ActionConfig, chunk: NarrativeGenChunk) -> NarrativeFrame:
        provided = chunk.seed_blocks
        if len(provided) >= chunk.lesson_blocks:
            return NarrativeFrame(blocks=provided[:chunk.lesson_blocks])

        language_config = config.language
        curriculum = config.curriculum
        step_config = build_narrative_generator_language_config(language_config)
        prompt = build_narrative_generator_prompt(
            theme=chunk.theme,
            level_details=curriculum.level_details,
            lesson_blocks=chunk.lesson_blocks,
            canonical_language=step_config.canonical_language,
            seed_blocks=provided,
        )
        result = config.runtime.call_llm(prompt)
        generated = [
            (block.get("narrative") or "").strip()
            for block in result.get("blocks", [])
            if isinstance(block, dict)
        ]
        defaults = step_config.default_block_builder(
            chunk.theme,
            curriculum.level_details,
            chunk.lesson_blocks,
        )
        blocks = list(provided)
        for text in generated:
            if text and len(blocks) < chunk.lesson_blocks:
                blocks.append(text)
        while len(blocks) < chunk.lesson_blocks:
            blocks.append(defaults[len(blocks)])
        return NarrativeFrame(blocks=blocks[:chunk.lesson_blocks])
