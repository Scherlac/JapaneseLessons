from __future__ import annotations

from datetime import datetime, timezone

from .action import PersistContentAction, PersistContentRequest
from ..pipeline_core import (
    ActionStep,
    LessonContext,
    LessonRegistrationArtifact,
    PersistedContentArtifact,
)


class PersistContentStep(ActionStep[PersistContentRequest, PersistedContentArtifact]):
    """Step 8 — Save LessonContent to output/<lesson_id>/content.json."""

    name = "persist_content"
    description = "Save LessonContent to output/<id>/content.json"
    _action = PersistContentAction()

    @property
    def action(self) -> PersistContentAction:
        return self._action

    def should_skip(self, ctx: LessonContext) -> bool:
        return ctx.content_path is not None

    def build_input(self, ctx: LessonContext) -> list[PersistContentRequest]:
        created_at = ctx.created_at or (
            datetime.now(timezone.utc)
            .isoformat(timespec="seconds")
            .replace("+00:00", "Z")
        )
        registration = LessonRegistrationArtifact(
            lesson_id=ctx.lesson_id,
            created_at=created_at,
            curriculum=ctx.curriculum,
            header_markdown="",
        )
        return [
            PersistContentRequest(
                registration=registration,
                theme=ctx.config.theme,
                language=ctx.config.language,
                narrative_blocks=ctx.narrative_blocks,
                grammar_ids=[grammar.id for grammar in ctx.selected_grammar],
                noun_items=list(ctx.noun_items),
                verb_items=list(ctx.verb_items),
                sentences=list(ctx.sentences),
                completed_steps=list(ctx.completed_steps),
                step_timings=dict(ctx.step_timings),
                step_details=dict(ctx.step_details),
                pipeline_started_at=ctx.pipeline_started_at,
            )
        ]

    def merge_output(self, ctx: LessonContext, outputs: list[PersistedContentArtifact]) -> LessonContext:
        result = outputs[-1]
        ctx.persisted_content = result
        ctx.created_at = result.created_at
        ctx.content_path = result.content_path
        if result.content_path is not None:
            ctx.report.add_artifact("Content JSON", result.content_path)
            self._log(ctx, f"       {result.content_path}")
        return ctx