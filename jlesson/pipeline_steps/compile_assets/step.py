from __future__ import annotations

from jlesson.lesson_pipeline.pipeline_paths import resolve_lesson_dir
from jlesson.models import GeneralItem, Phase, Sentence

from .action import AssetCompileRequest, CompileAssetsAction
from ..pipeline_core import ActionStep, GeneralItemSequence, LessonBlock, LessonContext, LessonPlan


class CompileAssetsStep(ActionStep[LessonBlock, LessonBlock]):
    """Step 9 — Render card images + TTS audio per item (Stage 2)."""

    name = "compile_assets"
    description = "Render card images + TTS audio per item"
    _action = CompileAssetsAction()

    @property
    def action(self) -> CompileAssetsAction:
        return self._action


    def should_skip(self, ctx: LessonContext) -> bool:
        if ctx.lesson_plan is None:
            self._log(ctx, "       no lesson plan — skipping compile_assets")
            return True
        return False

    def build_input_list(self, ctx: LessonContext) -> list[LessonBlock]:
        items_by_phase = ctx.lesson_plan.blocks
        total_items = sum(len(seq_list) for items in items_by_phase for seq_list in items.content_sequences.values())

        if ctx.config.dry_run:
            self._log(ctx, f"       (dry-run) {total_items} items - cards only")
        else:
            self._log(ctx, f"       {total_items} items -> cards + TTS")

        return items_by_phase

    def merge_output_list(self, ctx: LessonContext, outputs: list[LessonBlock]) -> LessonContext:
        ctx.lesson_plan = LessonPlan(
            theme=ctx.lesson_plan.theme,
            lesson_number=ctx.lesson_plan.lesson_number,
            blocks=outputs,
        )
        total_items = sum(
            len(seq_list)
            for block in outputs
            for seq_list in block.content_sequences.values()
        )
        self._log(ctx, f"       {total_items} compiled items")
        return ctx