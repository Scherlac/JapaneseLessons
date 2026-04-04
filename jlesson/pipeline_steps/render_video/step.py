from __future__ import annotations

from jlesson.lesson_pipeline.pipeline_paths import resolve_lesson_dir
from jlesson.models import VideoCard

from .action import RenderVideoAction, RenderVideoRequest
from ..pipeline_core import ActionStep, LessonContext, RenderedVideoArtifact


class RenderVideoStep(ActionStep[RenderVideoRequest, RenderedVideoArtifact]):
    """Step 11 — Assemble MP4 from touch sequence."""

    name = "render_video"
    description = "Assemble MP4 from touch sequence"
    _action = RenderVideoAction()

    @property
    def action(self) -> RenderVideoAction:
        return self._action

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

    def should_skip(self, ctx: LessonContext) -> bool:
        return bool(ctx.video_path)

    def build_chunks(self, ctx: LessonContext) -> list[RenderVideoRequest]:
        if not ctx.config.render_video or ctx.config.dry_run:
            reason = "dry-run" if ctx.config.dry_run else "skipped"
            self._log(ctx, f"       ({reason})")
            return []

        lesson_dir = resolve_lesson_dir(ctx.config, ctx.lesson_id)
        return [RenderVideoRequest(items=ctx.touches, lesson_dir=lesson_dir)]

    def merge_outputs(self, ctx: LessonContext, outputs: list[RenderedVideoArtifact]) -> LessonContext:
        if not outputs:
            return ctx

        result = outputs[-1]
        ctx.rendered_video = result
        lesson_dir = resolve_lesson_dir(ctx.config, ctx.lesson_id)
        video_path = lesson_dir / "lesson.mp4"

        self._log(ctx, f"       {result.clip_count} clips -> {video_path.name}")

        ctx.video_path = result.video_path
        if result.video_path is not None:
            size_kb = result.video_path.stat().st_size // 1024
            self._log(ctx, f"       OK  ({size_kb} KB)")
            ctx.report.add_artifact("Video", result.video_path)

        if result.cards_dir is not None:
            ctx.report.add_artifact("Cards", result.cards_dir)
        if result.audio_dir is not None:
            ctx.report.add_artifact("Audio", result.audio_dir)
        return ctx