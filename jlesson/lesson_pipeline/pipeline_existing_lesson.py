from __future__ import annotations

import asyncio
from pathlib import Path

from jlesson.asset_compiler import compile_assets
from jlesson.language_config import get_language_config
from jlesson.lesson_store import load_lesson_content
from jlesson.models import Phase
from jlesson.profiles import get_profile
from jlesson.touch_compiler import compile_touches
from jlesson.video.builder import VideoBuilder

from .pipeline_core import LessonConfig
from .pipeline_paths import resolve_output_dir


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
    resolved_output_dir = resolve_output_dir(config)
    content = load_lesson_content(lesson_id, resolved_output_dir)
    lang_cfg = get_language_config(content.language or language)
    profile_obj = get_profile(profile)

    items_by_phase = {
        Phase.NOUNS: content.noun_items,
        Phase.VERBS: content.verb_items,
        Phase.GRAMMAR: content.sentences,
    }

    lesson_dir = resolved_output_dir / f"lesson_{lesson_id:03d}"
    compiled_items = asyncio.run(
        compile_assets(
            items_by_phase,
            profile_obj,
            output_dir=lesson_dir,
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