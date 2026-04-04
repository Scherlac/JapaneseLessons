from __future__ import annotations

from jlesson.lesson_pipeline.pipeline_paths import resolve_lesson_dir

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

    def should_skip(self, ctx: LessonContext) -> bool:
        return ctx.rendered_video is not None

    def build_input(self, ctx: LessonContext) -> RenderVideoRequest:
        if not ctx.config.render_video or ctx.config.dry_run:
            reason = "dry-run" if ctx.config.dry_run else "skipped"
            self._log(ctx, f"       ({reason})")
            return None

        lesson_dir = resolve_lesson_dir(ctx.config)
        touches = ctx.touch_sequence.items if ctx.touch_sequence else []
        return RenderVideoRequest(items=touches, lesson_dir=lesson_dir)

    def merge_output(self, ctx: LessonContext, outputs: RenderedVideoArtifact) -> LessonContext:
        if not outputs:
            return ctx

        result = outputs
        ctx.rendered_video = result
        lesson_dir = resolve_lesson_dir(ctx.config)
        video_path = lesson_dir / "lesson.mp4"

        self._log(ctx, f"       {result.clip_count} clips -> {video_path.name}")

        if result.video_path is not None:
            size_kb = result.video_path.stat().st_size // 1024
            self._log(ctx, f"       OK  ({size_kb} KB)")
            ctx.report.add_artifact("Video", result.video_path)

        if result.cards_dir is not None:
            ctx.report.add_artifact("Cards", result.cards_dir)
        if result.audio_dir is not None:
            ctx.report.add_artifact("Audio", result.audio_dir)
        return ctx