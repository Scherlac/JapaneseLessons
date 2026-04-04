from __future__ import annotations

from datetime import datetime, timezone

from jlesson.models import Phase

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

    def build_input(self, ctx: LessonContext) -> PersistContentRequest:
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

        # Derive noun_items and verb_items from the resolved lesson plan
        noun_items = []
        verb_items = []
        if ctx.lesson_plan is not None:
            for block in ctx.lesson_plan.blocks:
                noun_items.extend(block.content_sequences.get(Phase.NOUNS, []))
                verb_items.extend(block.content_sequences.get(Phase.VERBS, []))

        # Derive grammar_ids from the canonical plan (source of truth for grammar IDs)
        grammar_ids: list[str] = []
        if ctx.canonical_plan is not None:
            seen: set[str] = set()
            for block in ctx.canonical_plan.blocks:
                for gid in block.grammar_ids:
                    if gid not in seen:
                        seen.add(gid)
                        grammar_ids.append(gid)
        elif ctx.lesson_plan is not None:
            grammar_ids = ctx.lesson_plan.grammar_ids

        # Narrative blocks from the narrative frame (extract plain narrative string for persistence)
        narrative_blocks = (
            [nb.narrative for nb in ctx.narrative_frame.blocks]
            if ctx.narrative_frame is not None else []
        )

        # Sentences: populated later when a sentence-generation step is added
        sentences = getattr(ctx, "sentences", []) or []

        return PersistContentRequest(
            registration=registration,
            theme=ctx.config.theme,
            language=ctx.config.language,
            narrative_blocks=narrative_blocks,
            grammar_ids=grammar_ids,
            noun_items=noun_items,
            verb_items=verb_items,
            sentences=sentences,
            completed_steps=list(ctx.completed_steps),
            step_timings=dict(ctx.step_timings),
            step_details=dict(ctx.step_details),
            pipeline_started_at=ctx.pipeline_started_at,
        )

    def merge_output(self, ctx: LessonContext, outputs: PersistedContentArtifact) -> LessonContext:
        result = outputs
        ctx.persisted_content = result
        ctx.created_at = result.created_at
        ctx.content_path = result.content_path
        if result.content_path is not None:
            ctx.report.add_artifact("Content JSON", result.content_path)
            self._log(ctx, f"       {result.content_path}")
        return ctx