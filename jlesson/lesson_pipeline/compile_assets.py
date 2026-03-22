from __future__ import annotations

import asyncio
import jlesson.asset_compiler as asset_compiler
from jlesson.models import Phase
from .pipeline_core import LessonContext, PipelineStep
from .pipeline_paths import resolve_output_dir
from jlesson.profiles import get_profile


class CompileAssetsStep(PipelineStep):
    """Step 9 — Render card images + TTS audio per item (Stage 2)."""

    name = "compile_assets"
    description = "Render card images + TTS audio per item"

    @staticmethod
    def build_items_by_phase(ctx: LessonContext) -> dict[Phase, list]:
        return {
            Phase.NOUNS: ctx.noun_items,
            Phase.VERBS: ctx.verb_items,
            Phase.GRAMMAR: ctx.sentences,
        }

    def execute(self, ctx: LessonContext) -> LessonContext:
        items_by_phase = self.build_items_by_phase(ctx)
        profile = get_profile(ctx.config.profile)
        output_dir = resolve_output_dir(ctx.config)
        lesson_dir = output_dir / f"lesson_{ctx.lesson_id:03d}"

        total_items = sum(len(items) for items in items_by_phase.values())

        if ctx.config.dry_run:
            self._log(ctx, f"       (dry-run) {total_items} items - cards only")
            ctx.compiled_items = asset_compiler.compile_assets_sync(
                items_by_phase,
                profile,
                ctx.step_info,
                lesson_dir,
                lang_cfg=ctx.language_config,
            )
        else:
            self._log(ctx, f"       {total_items} items -> cards + TTS")
            ctx.compiled_items = asyncio.run(
                asset_compiler.compile_assets(
                    items_by_phase,
                    profile,
                    ctx.step_info,
                    lesson_dir,
                    lang_cfg=ctx.language_config,
                )
            )

        self._log(ctx, f"       {len(ctx.compiled_items)} compiled items")
        return ctx