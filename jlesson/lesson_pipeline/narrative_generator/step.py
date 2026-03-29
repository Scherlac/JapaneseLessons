from __future__ import annotations

from ..pipeline_core import LessonContext, PipelineStep
from ..runtime import PipelineRuntime
from .config import build_narrative_generator_language_config
from .prompt import build_narrative_generator_prompt


class NarrativeGeneratorStep(PipelineStep):
    """Generate or normalize a narrative progression across lesson blocks."""

    name = "narrative_generator"
    description = "LLM: generate block-by-block narrative progression"

    def execute(self, ctx: LessonContext) -> LessonContext:
        if ctx.narrative_blocks:
            self._log(ctx, "       using existing narrative blocks")
            return ctx

        block_count = max(1, ctx.config.lesson_blocks)
        provided = [text.strip() for text in ctx.config.narrative if text.strip()]
        if len(provided) >= block_count:
            ctx.narrative_blocks = provided[:block_count]
        else:
            lesson_number = len(ctx.curriculum.lessons) + 1
            step_config = build_narrative_generator_language_config(ctx.language_config)
            prompt = build_narrative_generator_prompt(
                theme=ctx.config.theme,
                lesson_number=lesson_number,
                lesson_blocks=block_count,
                source_language_label=step_config.source_language_label,
                seed_blocks=provided,
            )
            result = PipelineRuntime.ask_llm(ctx, prompt)
            generated = [
                (block.get("narrative") or "").strip()
                for block in result.get("blocks", [])
                if isinstance(block, dict)
            ]
            if len(generated) < block_count:
                self._log(ctx, f"       LLM returned {len(generated)}/{block_count} blocks — filling with defaults")
            defaults = step_config.default_block_builder(
                ctx.config.theme,
                lesson_number,
                block_count,
            )
            blocks = list(provided)
            for text in generated:
                if text and len(blocks) < block_count:
                    blocks.append(text)
            while len(blocks) < block_count:
                blocks.append(defaults[len(blocks)])
            ctx.narrative_blocks = blocks[:block_count]

        self._log(ctx, f"       {len(ctx.narrative_blocks)} narrative blocks")
        ctx.report.add("narrative", self._render_narrative(ctx.narrative_blocks))
        return ctx

    @staticmethod
    def _render_narrative(blocks: list[str]) -> str:
        lines = ["## Narrative Progression", ""]
        for index, block in enumerate(blocks, 1):
            lines.extend([f"### Block {index}", "", block, ""])
        return "\n".join(lines)
