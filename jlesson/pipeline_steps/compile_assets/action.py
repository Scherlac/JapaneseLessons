from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path

import jlesson.asset_compiler as asset_compiler
from jlesson.lesson_pipeline.pipeline_paths import resolve_lesson_dir
from jlesson.models import GeneralItem, GeneralItem, Phase, Sentence
from jlesson.profiles import get_profile
from tests.test_lesson_pipeline import ctx

from ..pipeline_core import ActionConfig, GeneralItemSequence, LessonBlock, StepAction


@dataclass
class AssetCompileRequest:
    """Single render-compilation request for one lesson output bundle."""

    items_by_phase: dict[Phase, list[GeneralItem | Sentence]]
    lesson_dir: Path
    dry_run: bool


class CompileAssetsAction(StepAction[LessonBlock, LessonBlock]):
    """Render cards/audio and return the compiled-item sequence artifact."""

    def run(self, config: ActionConfig, input: LessonBlock) -> LessonBlock:
        profile = get_profile(config.lesson.profile)
        lesson_dir = resolve_lesson_dir(config.lesson)

        items = asyncio.run(
            asset_compiler.compile_assets(
                input.content_sequences,
                profile,
                lesson_dir,
                lang_cfg=config.language,
            )
        )

        return input