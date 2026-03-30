from __future__ import annotations

from pathlib import Path

from jlesson.asset_compiler import compile_assets_sync
from jlesson.language_config import get_language_config
from jlesson.lesson_store import load_lesson_content
from jlesson.models import GeneralItem, Phase
from jlesson.pipeline_steps.pipeline_core import LessonConfig
from jlesson.profiles import Profile, get_profile
from jlesson.touch_compiler import compile_touches
from jlesson.video.builder import VideoBuilder

from .pipeline_paths import resolve_lesson_dir, resolve_output_dir


def _wire_existing_assets(
    items_by_phase: dict[Phase, list[GeneralItem]],
    profile: Profile,
    lesson_dir: Path,
) -> list[GeneralItem]:
    """Attach existing on-disk asset paths to items without re-rendering anything."""
    cards_dir = lesson_dir / "cards"
    audio_dir = lesson_dir / "audio"

    compiled: list[GeneralItem] = []
    item_index = 0

    # Asset key → card filename suffix mapping (mirrors asset_compiler logic)
    _card_suffix = {
        "card_src": "src",
        "card_tar": "tar",
        "card_src_tar": "src_tar",
    }

    for phase in (Phase.NOUNS, Phase.VERBS, Phase.GRAMMAR):
        items = items_by_phase.get(phase, [])
        required = profile.required_assets(phase)

        for item in items:
            item_index += 1

            for asset_key in required:
                if asset_key.startswith("card_"):
                    suffix = _card_suffix.get(asset_key)
                    if suffix:
                        path = cards_dir / f"{item_index:03d}_{suffix}.png"
                        if path.exists():
                            if "src" in asset_key and asset_key != "card_src_tar":
                                item.source.assets[asset_key] = path
                            else:
                                item.target.assets[asset_key] = path
                elif asset_key.startswith("audio_"):
                    path = audio_dir / f"{item_index:03d}_{asset_key}.mp3"
                    if path.exists():
                        if asset_key == "audio_src":
                            item.source.assets[asset_key] = path
                        else:
                            item.target.assets[asset_key] = path

            item_copy = item.model_copy()
            item_copy.phase = phase
            compiled.append(item_copy)

    return compiled


def render_existing_lesson(
    lesson_id: int,
    output_dir: Path | None = None,
    theme: str = "",
    profile: str = "passive_video",
    language: str = "eng-jap",
    recompile_cards: bool = False,
    verbose: bool = True,
) -> Path:
    """Render MP4 for an already-generated lesson content file."""
    config = LessonConfig(
        theme=theme,
        curriculum_path=Path("curriculum/curriculum.json"),
        output_dir=output_dir,
        profile=profile,
        language=language,
        verbose=verbose,
    )
    content = load_lesson_content(lesson_id, resolve_lesson_dir(config, lesson_id))
    profile_obj = get_profile(profile)

    items_by_phase = {
        Phase.NOUNS: content.noun_items,
        Phase.VERBS: content.verb_items,
        Phase.GRAMMAR: content.sentences,
    }
    total_items = sum(len(v) for v in items_by_phase.values())

    lesson_dir = resolve_lesson_dir(config, lesson_id)

    if verbose:
        print(f"  Lesson {lesson_id:03d}  |  {total_items} items  |  profile: {profile}")
        print(f"  Assets dir : {lesson_dir}")

    if recompile_cards:
        if verbose:
            print("  Recompiling cards ...")
        lang_cfg = get_language_config(language)
        compile_assets_sync(
            items_by_phase,
            profile_obj,
            output_dir=lesson_dir,
            lang_cfg=lang_cfg,
        )
        if verbose:
            print("  Cards done.")

    compiled_items = _wire_existing_assets(items_by_phase, profile_obj, lesson_dir)
    touches = compile_touches(compiled_items, profile_obj)

    if verbose:
        print(f"  Touches    : {len(touches)}")
        print(f"  FFmpeg     : {'available' if VideoBuilder()._ffmpeg_available else 'not found — using MoviePy'}")
        print(f"  Building clips ...")

    video_builder = VideoBuilder()
    clips = []
    for touch in touches:
        card_path = touch.artifacts.get("card")
        if card_path is None or not card_path.exists():
            continue
        audio_paths = touch.artifacts.get("audio") or []
        clip = video_builder.create_multi_audio_clip(card_path, audio_paths)
        clips.append(clip)

    video_path = resolve_lesson_dir(config, lesson_id) / "lesson.mp4"
    if not clips:
        raise ValueError(
            f"No renderable clips found for lesson {lesson_id}. "
            "Check compiled assets under the lesson output directory."
        )

    if verbose:
        print(f"  Assembling {len(clips)} clips -> {video_path.name}")

    video_builder.build_video(clips, video_path, method="ffmpeg")
    if verbose:
        print(f"  Done: {video_path}")
    return video_path