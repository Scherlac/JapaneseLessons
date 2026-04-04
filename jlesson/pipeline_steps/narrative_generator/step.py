from __future__ import annotations

from ..pipeline_core import ActionStep, LessonContext, NarrativeFrame, NarrativeGenChunk
from .action import NarrativeGeneratorAction


class NarrativeGeneratorStep(ActionStep[NarrativeGenChunk, NarrativeFrame]):
    """Generate or normalise a narrative progression across lesson blocks.

    Inputs (from ``LessonContext``)
    --------------------------------
    config.narrative        list[str]  — optional user-provided seed blocks
    config.lesson_blocks    int        — desired block count
    config.theme            str        — lesson theme
    curriculum              used to derive ``lesson_number``

    Output
    ------
    narrative_blocks        list[str]  written back to ``LessonContext``

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
        if ctx.narrative_blocks:
            self._log(ctx, "       using existing narrative blocks")
            return True
        return False

    def build_chunks(self, ctx: LessonContext) -> list[NarrativeGenChunk]:
        block_count = max(1, ctx.config.lesson_blocks)
        provided = [text.strip() for text in ctx.config.narrative if text.strip()]
        lesson_number = len(ctx.curriculum.lessons) + 1
        return [NarrativeGenChunk(
            theme=ctx.config.theme,
            lesson_number=lesson_number,
            lesson_blocks=block_count,
            seed_blocks=provided,
        )]

    def merge_outputs(self, ctx: LessonContext, outputs: list[NarrativeFrame]) -> LessonContext:
        frame = outputs[0]
        ctx.narrative_frame = frame
        self._log(ctx, f"       {len(ctx.narrative_blocks)} narrative blocks")
        ctx.report.add("narrative", self._render_narrative(ctx.narrative_blocks))
        return ctx

    @staticmethod
    def _render_narrative(blocks: list[str]) -> str:
        lines = ["## Narrative Progression", ""]
        for index, block in enumerate(blocks, 1):
            lines.extend([f"### Block {index}", "", block, ""])
        return "\n".join(lines)
