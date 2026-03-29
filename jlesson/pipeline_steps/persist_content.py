from __future__ import annotations

from datetime import datetime, timezone

from jlesson.lesson_pipeline.pipeline_paths import resolve_lesson_dir, resolve_vocab_dir
from jlesson.models import LessonContent
from .pipeline_core import LessonContext, PipelineStep
from jlesson.lesson_store import save_lesson_content, save_shared_vocab


def _item_to_vocab_dict(item) -> dict:
    if isinstance(item, dict):
        return item
    source_text = item.source.display_text or ""
    d = {**item.source.extra, **item.target.extra}
    d["id"] = source_text.strip().lower()
    d["source"] = source_text
    d["target"] = item.target.display_text or ""
    d["phonetic"] = item.target.pronunciation or ""
    return d


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
            grammar_ids=[g.id for g in ctx.selected_grammar],
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
        lesson_dir = resolve_lesson_dir(ctx.config, ctx.lesson_id)
        ctx.content_path = save_lesson_content(content, lesson_dir)
        ctx.report.add_artifact("Content JSON", ctx.content_path)
        self._log(ctx, f"       {ctx.content_path}")

        vocab_path = save_shared_vocab(
            resolve_vocab_dir(ctx.config),
            ctx.config.theme,
            [_item_to_vocab_dict(n) for n in ctx.noun_items],
            [_item_to_vocab_dict(v) for v in ctx.verb_items],
        )
        self._log(ctx, f"       vocab  {vocab_path}")
        return ctx