from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import jlesson.video.builder as video_builder_module

from ..pipeline_core import ActionConfig, RenderedVideoArtifact, StepAction, TouchSequence


@dataclass
class RenderVideoRequest(TouchSequence):
    """Composite successor chunk preserving touches as the core predecessor artifact."""

    lesson_dir: Path


class RenderVideoAction(StepAction[RenderVideoRequest, RenderedVideoArtifact]):
    """Assemble a lesson video from an ordered touch sequence."""

    def run(self, config: ActionConfig, chunk: RenderVideoRequest) -> RenderedVideoArtifact:
        video_builder = video_builder_module.VideoBuilder()
        video_path = chunk.lesson_dir / "lesson.mp4"

        clips = []
        for touch in chunk.items:
            card_path = touch.artifacts.get("card")
            if card_path is None or not card_path.exists():
                continue
            audio_paths = touch.artifacts.get("audio") or []
            clip = video_builder.create_multi_audio_clip(card_path, audio_paths)
            clips.append(clip)

        if clips:
            video_builder.build_video(clips, video_path, method="ffmpeg")
            built_video_path: Path | None = video_path
        else:
            built_video_path = None

        cards_dir = chunk.lesson_dir / "cards"
        audio_dir = chunk.lesson_dir / "audio"
        return RenderedVideoArtifact(
            video_path=built_video_path,
            clip_count=len(clips),
            cards_dir=cards_dir if cards_dir.exists() else None,
            audio_dir=audio_dir if audio_dir.exists() else None,
        )