from __future__ import annotations

import re
from pathlib import Path

from ..pipeline_core import ActionStep, LessonContext, NarrativeFrame, NarrativeConfig
from .action import NarrativeGeneratorAction


def _parse_srt(path: Path) -> str:
    """Return plain dialogue text extracted from an SRT subtitle file.

    Strips subtitle sequence numbers, timestamp lines, and blank lines so the
    LLM receives only the spoken dialogue as a compact block of text.
    """
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    result: list[str] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.isdigit():
            continue
        if re.match(r"\d{2}:\d{2}:\d{2},\d{3}\s*-->", line):
            continue
        result.append(line)
    return "\n".join(result)


class NarrativeGeneratorStep(ActionStep[NarrativeConfig, NarrativeFrame]):
    """Generate or normalise a narrative progression across lesson blocks.

    Inputs (from ``LessonContext``)
    --------------------------------
    config.narrative        list[str]  — optional user-provided seed blocks
    config.lesson_blocks    int        — desired block count
    config.theme            str        — lesson theme
    curriculum              used to derive ``lesson_number``

    Output
    ------
    narrative_frame        NarrativeFrame  written back to ``LessonContext``

    The action emits a ``NarrativeFrame`` which is also the direct input chunk
    type for the successor step ``ExtractNarrativeVocabStep``, making the
    inter-step dependency explicit and typed.
    """

    name = "narrative_generator"
    description = "LLM: generate block-by-block narrative progression"

    @property
    def action(self) -> NarrativeGeneratorAction:
        return NarrativeGeneratorAction()

    def should_skip(self, ctx: LessonContext) -> bool:
        if ctx.narrative_frame:
            self._log(ctx, "       using existing narrative blocks")
            return True
        return False

    def build_input(self, ctx: LessonContext) -> NarrativeConfig:

        block_count = max(1, ctx.config.lesson_blocks)
        provided = [text.strip() for text in ctx.config.narrative if text.strip()]
        lesson_number = len(ctx.curriculum.lessons) + 1

        raw_script = ""
        if ctx.config.subtitle_file is not None:
            raw_script = _parse_srt(ctx.config.subtitle_file)

        return NarrativeConfig(
            theme=ctx.config.theme,
            lesson_number=lesson_number,
            lesson_blocks=block_count,
            seed_blocks=provided,
            raw_script=raw_script,
        )

    def merge_output(self, ctx: LessonContext, outputs: NarrativeFrame) -> LessonContext:
        frame = outputs
        ctx.narrative_frame = frame
        self._log(ctx, f"       {len(ctx.narrative_frame.blocks)} narrative blocks")
        return ctx
