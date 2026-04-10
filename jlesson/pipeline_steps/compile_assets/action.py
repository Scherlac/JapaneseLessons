from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path

import jlesson.asset_compiler as asset_compiler
from jlesson.asset_compiler import build_asset_suffix_map
from jlesson.lesson_pipeline.pipeline_paths import resolve_lesson_dir
from jlesson.models import GeneralItem, Phase, Sentence
from jlesson.profiles import get_profile

from ..pipeline_core import ActionConfig, LessonBlock, StepAction

# Re-export for use by cli.py bundle command
_SOURCE_ASSET_KEYS: frozenset[str] = frozenset({"audio_src", "card_src"})


@dataclass
class AssetCompileRequest:
    """Single render-compilation request for one lesson output bundle."""

    items_by_phase: dict[Phase, list[GeneralItem | Sentence]]
    lesson_dir: Path
    dry_run: bool


class CompileAssetsAction(StepAction[LessonBlock, LessonBlock]):
    """Render cards/audio and return the compiled-item sequence artifact.

    Resolution order for each asset:
      1. RCM central store  (rcm_path / assets / ...)
      2. Project-level dir  (output_dir / language / assets / ...)  [manual drop zone]
      3. Lesson-level dirs  (lesson_dir / audio / ... and lesson_dir / cards / ...)

    After compile_assets() runs, every newly rendered file is copied into the
    RCM central store and registered with a relative path.
    """

    def run(self, config: ActionConfig, input: LessonBlock) -> LessonBlock:
        profile = get_profile(config.lesson.profile)
        lesson_dir = resolve_lesson_dir(config.lesson)
        lang = config.language.code if config.language else ""
        suffix_map = build_asset_suffix_map(lang)

        if config.rcm is not None:
            project_assets_dir = (
                Path(config.lesson.output_dir) / lang / "assets"
                if config.lesson.output_dir
                else None
            )
            config.rcm.pre_populate_assets(
                input.content_sequences, suffix_map, lang, project_assets_dir
            )

        asyncio.run(
            asset_compiler.compile_assets(
                input.content_sequences,
                profile,
                lesson_dir,
                lang_cfg=config.language,
            )
        )

        if config.rcm is not None:
            config.rcm.post_register_assets(
                input.content_sequences, suffix_map, lang, lesson_dir
            )

        return input