from __future__ import annotations

import asyncio
import time
from pathlib import Path

from .asset_compiler import compile_assets
from .language_config import get_language_config
from .lesson_store import load_lesson_content
from .models import Phase
from .pipeline_core import LessonConfig, LessonContext, PipelineStep, StepInfo
from .pipeline_gadgets import PipelineGadgets
from .profiles import get_profile
from .touch_compiler import compile_touches
from .video.builder import VideoBuilder


def run_pipeline(
    config: LessonConfig,
    *,
    pipeline: list[PipelineStep],
    load_curriculum_fn,
) -> LessonContext:
    """Run the full lesson generation pipeline."""
    ctx = LessonContext(config=config)
    ctx.language_config = get_language_config(config.language)
    ctx.curriculum = load_curriculum_fn(config.curriculum_path)
    total = len(pipeline)

    print(f"\n{'=' * 60}")
    print(f"  LESSON: {config.theme.upper()}")
    print(f"{'=' * 60}")

    t_total = time.time()
    for index, step in enumerate(pipeline, 1):
        info = StepInfo(
            index=index,
            total=total,
            name=step.name,
            description=step.description,
        )
        ctx.step_info = info
        if config.verbose:
            print(f"\n  {info.label} {step.description}")
        t_step = time.time()
        ctx = step.execute(ctx)
        ctx.report.record_time(step.name, time.time() - t_step)

    elapsed = time.time() - t_total
    print(f"\n  Done - {elapsed:.0f}s")
    if ctx.video_path and ctx.video_path.exists():
        print(f"  Video   : {ctx.video_path}")
    if ctx.content_path:
        print(f"  Content : {ctx.content_path}")
    if ctx.report_path:
        print(f"  Report  : {ctx.report_path}")
    return ctx


def render_existing_lesson(
    lesson_id: int,
    output_dir: Path | None = None,
    profile: str = "passive_video",
    language: str = "eng-jap",
    verbose: bool = True,
) -> Path:
    """Render MP4 for an already-generated lesson content file."""
    config = LessonConfig(
        theme="",
        curriculum_path=Path("curriculum/curriculum.json"),
        output_dir=output_dir,
        profile=profile,
        language=language,
        verbose=verbose,
    )
    resolved_output_dir = PipelineGadgets.resolve_output_dir(config)
    content = load_lesson_content(lesson_id, resolved_output_dir)
    lang_cfg = get_language_config(content.language or language)
    profile_obj = get_profile(profile)

    items_by_phase = {
        Phase.NOUNS: content.noun_items,
        Phase.VERBS: content.verb_items,
        Phase.GRAMMAR: content.sentences,
    }

    lesson_dir = resolved_output_dir / f"lesson_{lesson_id:03d}"
    step_info = StepInfo(
        index=9,
        total=12,
        name="compile_assets",
        description="Render card images + TTS audio per item",
    )

    compiled_items = asyncio.run(
        compile_assets(
            items_by_phase,
            profile_obj,
            step_info,
            lesson_dir,
            lang_cfg=lang_cfg,
        )
    )
    touches = compile_touches(compiled_items, profile_obj)

    video_builder = VideoBuilder()
    clips = []
    for touch in touches:
        card_path = touch.artifacts.get("card")
        if card_path is None or not card_path.exists():
            continue
        audio_paths = touch.artifacts.get("audio") or []
        clip = video_builder.create_multi_audio_clip(card_path, audio_paths)
        clips.append(clip)

    video_path = resolved_output_dir / f"lesson_{lesson_id:03d}_{content.theme}.mp4"
    if not clips:
        raise ValueError(
            f"No renderable clips found for lesson {lesson_id}. "
            "Check compiled assets under the lesson output directory."
        )

    video_builder.build_video(clips, video_path, method="ffmpeg")
    if verbose:
        print(f"  Rendered {len(clips)} clips -> {video_path}")
    return video_path