from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path

import jlesson.asset_compiler as asset_compiler
from jlesson.models import GeneralItem, GeneralItem, Phase, Sentence
from jlesson.profiles import get_profile

from ..pipeline_core import ActionConfig, GeneralItemSequence, StepAction


@dataclass
class AssetCompileRequest:
    """Single render-compilation request for one lesson output bundle."""

    items_by_phase: dict[Phase, list[GeneralItem | Sentence]]
    lesson_dir: Path
    dry_run: bool


class CompileAssetsAction(StepAction[AssetCompileRequest, GeneralItemSequence]):
    """Render cards/audio and return the compiled-item sequence artifact."""

    def run(self, config: ActionConfig, chunk: AssetCompileRequest) -> GeneralItemSequence:
        profile = get_profile(config.lesson.profile)

        if chunk.dry_run:
            items = asset_compiler.compile_assets_sync(
                chunk.items_by_phase,
                profile,
                None,
                chunk.lesson_dir,
                lang_cfg=config.language,
            )
        else:
            items = asyncio.run(
                asset_compiler.compile_assets(
                    chunk.items_by_phase,
                    profile,
                    None,
                    chunk.lesson_dir,
                    lang_cfg=config.language,
                )
            )

        return GeneralItemSequence(items=items)