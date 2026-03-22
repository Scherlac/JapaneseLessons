from __future__ import annotations

from datetime import datetime, timezone

from jlesson.models import LessonContent
from .pipeline_core import LessonContext, PipelineStep
from .pipeline_grammar import grammar_id
from .pipeline_paths import resolve_output_dir
from jlesson.lesson_store import save_lesson_content


class PersistContentStep(PipelineStep):
    """Step 8 — Save LessonContent to output/<lesson_id>/content.json."""

    name = "persist_content"
    description = "Save LessonContent to output/<id>/content.json"

    @staticmethod
    def build_content(ctx: LessonContext) -> LessonContent:
        words = []
        words.extend(ctx.noun_items)
        words.extend(ctx.verb_items)
        return LessonContent(
            lesson_id=ctx.lesson_id,
            theme=ctx.config.theme,
            language=ctx.config.language,
            narrative_blocks=ctx.narrative_blocks,
            grammar_ids=[
                grammar_id(g)
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

    def execute(self, ctx: LessonContext) -> LessonContext:
        content = self.build_content(ctx)
        output_dir = resolve_output_dir(ctx.config)
        ctx.content_path = save_lesson_content(content, output_dir)
        ctx.report.add_artifact("Content JSON", ctx.content_path)
        self._log(ctx, f"       {ctx.content_path}")
        return ctx