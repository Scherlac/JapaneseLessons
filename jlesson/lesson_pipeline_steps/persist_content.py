from __future__ import annotations

from datetime import datetime, timezone

from jlesson.models import LessonContent
from jlesson.lesson_store import save_lesson_content

from .runtime import lesson_pipeline_module


class PersistContentStep(lesson_pipeline_module().PipelineStep):
    """Step 8 — Save LessonContent to output/<lesson_id>/content.json."""

    name = "persist_content"
    description = "Save LessonContent to output/<id>/content.json"

    @staticmethod
    def build_content(ctx: lesson_pipeline_module().LessonContext) -> LessonContent:
        words = []
        words.extend(ctx.noun_items)
        words.extend(ctx.verb_items)
        return LessonContent(
            lesson_id=ctx.lesson_id,
            theme=ctx.config.theme,
            language=ctx.config.language,
            grammar_ids=[
                lesson_pipeline_module().PipelineGadgets.grammar_id(g)
                for g in ctx.selected_grammar
            ],
            words=words,
            sentences=ctx.sentences,
            created_at=ctx.created_at
            or (
                datetime.now(timezone.utc)
                .isoformat(timespec="seconds")
                .replace("+00:00", "Z")
            ),
        )

    def execute(self, ctx: lesson_pipeline_module().LessonContext) -> lesson_pipeline_module().LessonContext:
        pipeline = lesson_pipeline_module()
        content = self.build_content(ctx)
        output_dir = pipeline.PipelineGadgets.resolve_output_dir(ctx.config)
        ctx.content_path = save_lesson_content(content, output_dir)
        ctx.report.add_artifact("Content JSON", ctx.content_path)
        self._log(ctx, f"       {ctx.content_path}")
        return ctx