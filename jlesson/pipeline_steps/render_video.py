from __future__ import annotations

import jlesson.video.builder as video_builder_module
from jlesson.lesson_pipeline.pipeline_paths import resolve_lesson_dir
from jlesson.models import VideoCard
from .pipeline_core import LessonContext, PipelineStep


class RenderVideoStep(PipelineStep):
    """Step 11 — Assemble MP4 from touch sequence."""

    name = "render_video"
    description = "Assemble MP4 from touch sequence"

    @staticmethod
    def build_video_items(noun_items: list[dict], sentences: list[dict], tts_voice: str = "") -> list[VideoCard]:
        items: list[VideoCard] = []
        total = len(noun_items) + len(sentences)

        for index, noun in enumerate(noun_items, 1):
            target = noun.get("target", "")
            phonetic = noun.get("phonetic", "")
            reveal = f"{target}  ({phonetic})" if phonetic else target
            items.append(VideoCard(
                phase="Nouns",
                step="INTRODUCE",
                counter=f"{index}/{total}",
                prompt=noun.get("source", ""),
                reveal=reveal,
                tts_text=target,
                tts_voice=tts_voice,
            ))

        offset = len(noun_items)
        for index, sentence in enumerate(sentences, 1):
            items.append(VideoCard(
                phase="Grammar",
                step="TRANSLATE",
                counter=f"{offset + index}/{total}",
                prompt=sentence.get("source", ""),
                reveal=sentence.get("target", ""),
                tts_text=sentence.get("target", ""),
                tts_voice=tts_voice,
            ))

        return items

    def execute(self, ctx: LessonContext) -> LessonContext:
        if not ctx.config.render_video or ctx.config.dry_run:
            reason = "dry-run" if ctx.config.dry_run else "skipped"
            self._log(ctx, f"       ({reason})")
            return ctx

        lesson_dir = resolve_lesson_dir(ctx.config, ctx.lesson_id)
        video_path = lesson_dir / "lesson.mp4"

        video_builder = video_builder_module.VideoBuilder()
        clips = []
        for touch in ctx.touches:
            card_path = touch.artifacts.get("card")
            if card_path is None or not card_path.exists():
                continue
            audio_paths = touch.artifacts.get("audio") or []
            clip = video_builder.create_multi_audio_clip(card_path, audio_paths)
            clips.append(clip)

        self._log(ctx, f"       {len(clips)} clips -> {video_path.name}")

        if clips:
            video_builder.build_video(clips, video_path, method="ffmpeg")
            ctx.video_path = video_path
            size_kb = video_path.stat().st_size // 1024
            self._log(ctx, f"       OK  ({size_kb} KB)")
            ctx.report.add_artifact("Video", video_path)

        cards_dir = lesson_dir / "cards"
        audio_dir = lesson_dir / "audio"
        if cards_dir.exists():
            ctx.report.add_artifact("Cards", cards_dir)
        if audio_dir.exists():
            ctx.report.add_artifact("Audio", audio_dir)
        return ctx