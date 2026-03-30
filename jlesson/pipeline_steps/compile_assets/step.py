from __future__ import annotations

from jlesson.lesson_pipeline.pipeline_paths import resolve_lesson_dir
from jlesson.models import GeneralItem, Phase, Sentence

from .action import AssetCompileRequest, CompileAssetsAction
from ..pipeline_core import ActionStep, CompiledItemSequence, LessonContext


class CompileAssetsStep(ActionStep[AssetCompileRequest, CompiledItemSequence]):
    """Step 9 — Render card images + TTS audio per item (Stage 2)."""

    name = "compile_assets"
    description = "Render card images + TTS audio per item"
    _action = CompileAssetsAction()

    @property
    def action(self) -> CompileAssetsAction:
        return self._action

    @staticmethod
    def build_items_by_phase(ctx: LessonContext) -> dict[Phase, list[GeneralItem | Sentence]]:
        return {
            Phase.NOUNS: ctx.noun_items,
            Phase.VERBS: ctx.verb_items,
            Phase.GRAMMAR: ctx.sentences,
        }

    def should_skip(self, ctx: LessonContext) -> bool:
        return bool(ctx.compiled_items)

    def build_chunks(self, ctx: LessonContext) -> list[AssetCompileRequest]:
        items_by_phase = self.build_items_by_phase(ctx)
        total_items = sum(len(items) for items in items_by_phase.values())
        lesson_dir = resolve_lesson_dir(ctx.config, ctx.lesson_id)

        if ctx.config.dry_run:
            self._log(ctx, f"       (dry-run) {total_items} items - cards only")
        else:
            self._log(ctx, f"       {total_items} items -> cards + TTS")

        return [
            AssetCompileRequest(
                items_by_phase=items_by_phase,
                lesson_dir=lesson_dir,
                dry_run=ctx.config.dry_run,
            )
        ]

    def merge_outputs(self, ctx: LessonContext, outputs: list[CompiledItemSequence]) -> LessonContext:
        result = outputs[-1] if outputs else CompiledItemSequence(items=[])
        ctx.compiled_items = result.items
        self._log(ctx, f"       {len(ctx.compiled_items)} compiled items")
        return ctx