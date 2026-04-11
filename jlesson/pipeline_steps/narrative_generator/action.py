"""Stateless narrative generation action.

This module contains the pure transformation logic extracted from
``NarrativeGeneratorStep.execute``.  It has no knowledge of ``LessonContext``
and performs all I/O through ``config.runtime``, making it independently
testable with a mock runtime.
"""
from __future__ import annotations

from ..pipeline_core import ActionConfig, NarrativeBlock, NarrativeFrame, NarrativeConfig, StepAction
from .config import build_narrative_generator_language_config
from .prompt import build_narrative_generator_prompt, build_subtitle_narrative_prompt

# If the number of pre-split blocks from a narrative file differs from the
# requested lesson_blocks by more than this ratio, treat the file content as a
# raw script and ask the LLM to synthesise the correct number of blocks.
_BLOCK_MISMATCH_RATIO = 0.25


class NarrativeGeneratorAction(StepAction[NarrativeConfig, NarrativeFrame]):
    """Generate or pass through a narrative progression across lesson blocks.

    Input
    -----
    chunk : NarrativeConfig
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

    def run(self, config: ActionConfig, chunk: NarrativeConfig) -> NarrativeFrame:
        provided = chunk.seed_blocks
        if len(provided) >= chunk.lesson_blocks:
            seed_narrative_blocks = [NarrativeBlock(narrative=s) for s in provided[:chunk.lesson_blocks]]
            return NarrativeFrame(
                theme=chunk.theme,
                lesson_number=chunk.lesson_number,
                lesson_blocks=chunk.lesson_blocks,
                seed_blocks=provided,
                raw_script=chunk.raw_script,
                blocks=seed_narrative_blocks,
            )

        language_config = config.language
        curriculum = config.curriculum
        step_config = build_narrative_generator_language_config(language_config)

        # ------------------------------------------------------------------ #
        # Subtitle / raw-script path                                          #
        # Use the LLM to synthesise blocks from the full script when:        #
        #   - a raw_script is available (parsed from an SRT file), OR        #
        #   - seed_blocks were supplied but their count differs from the      #
        #     requested lesson_blocks by more than _BLOCK_MISMATCH_RATIO      #
        #     (i.e. the user fed a long pre-split narrative file into the     #
        #     wrong slot — the LLM reshapes it to the right count).           #
        # ------------------------------------------------------------------ #
        use_subtitle_path = bool(chunk.raw_script)
        if not use_subtitle_path and provided:
            ratio = abs(len(provided) - chunk.lesson_blocks) / max(chunk.lesson_blocks, 1)
            use_subtitle_path = ratio > _BLOCK_MISMATCH_RATIO

        if use_subtitle_path:
            script = chunk.raw_script or "\n".join(provided)
            prompt = build_subtitle_narrative_prompt(
                script=script,
                lesson_blocks=chunk.lesson_blocks,
                canonical_language=step_config.canonical_language,
                seed_blocks=provided if chunk.raw_script else [],
            )
        else:
            prompt = build_narrative_generator_prompt(
                theme=chunk.theme,
                level_details=curriculum.level_details,
                lesson_blocks=chunk.lesson_blocks,
                canonical_language=step_config.canonical_language,
                seed_blocks=provided,
            )
        result = config.runtime.call_llm(prompt)
        generated: list[NarrativeBlock] = [
            NarrativeBlock(
                narrative=(block.get("narrative") or "").strip(),
                alignment_notes=(block.get("alignment_notes") or "").strip(),
                sentiment=(block.get("sentiment") or "").strip(),
                engagement_note=(block.get("engagement_note") or "").strip(),
            )
            for block in result.get("blocks", [])
            if isinstance(block, dict) and (block.get("narrative") or "").strip()
        ]
        defaults = step_config.default_block_builder(
            chunk.theme,
            curriculum.level_details,
            chunk.lesson_blocks,
        )
        # When using the subtitle path the LLM rewrites the full progression,
        # so we start from an empty list rather than prepending seed blocks.
        blocks: list[NarrativeBlock] = [] if use_subtitle_path else [NarrativeBlock(narrative=s) for s in provided]
        for nb in generated:
            if len(blocks) < chunk.lesson_blocks:
                blocks.append(nb)
        while len(blocks) < chunk.lesson_blocks:
            blocks.append(NarrativeBlock(narrative=defaults[len(blocks)]))
        return NarrativeFrame(
            theme=chunk.theme,
            lesson_number=chunk.lesson_number,
            lesson_blocks=chunk.lesson_blocks,
            seed_blocks=provided,
            raw_script=chunk.raw_script,
            blocks=blocks[:chunk.lesson_blocks],
        )