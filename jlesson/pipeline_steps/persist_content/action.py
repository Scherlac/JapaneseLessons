from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from jlesson.models import GeneralItem, LessonContent, Sentence

from ..pipeline_core import (
    ActionConfig,
    LessonRegistrationArtifact,
    PersistedContentArtifact,
    StepAction,
)


@dataclass
class PersistContentRequest:
    """Composite content-persistence request aligned to lesson registration."""

    registration: LessonRegistrationArtifact
    theme: str
    language: str
    narrative_blocks: list[str]
    grammar_ids: list[str]
    noun_items: list[GeneralItem | dict]
    verb_items: list[GeneralItem | dict]
    sentences: list[Sentence]
    completed_steps: list[str] = None
    step_timings: dict[str, float] = None
    step_details: dict[str, dict] = None
    pipeline_started_at: str = ""

    def __post_init__(self):
        if self.completed_steps is None:
            self.completed_steps = []
        if self.step_timings is None:
            self.step_timings = {}
        if self.step_details is None:
            self.step_details = {}


class PersistContentAction(StepAction[PersistContentRequest, PersistedContentArtifact]):
    """Persist lesson content using the typed registration artifact."""

    def run(
        self,
        config: ActionConfig,
        chunk: PersistContentRequest,
    ) -> PersistedContentArtifact:
        created_at = chunk.registration.created_at or (
            datetime.now(timezone.utc)
            .isoformat(timespec="seconds")
            .replace("+00:00", "Z")
        )
        words = [*chunk.noun_items, *chunk.verb_items]
        content = LessonContent(
            lesson_id=chunk.registration.lesson_id,
            theme=chunk.theme,
            language=chunk.language,
            narrative_blocks=chunk.narrative_blocks,
            grammar_ids=chunk.grammar_ids,
            words=words,
            sentences=chunk.sentences,
            created_at=created_at,
            pipeline_started_at=chunk.pipeline_started_at,
            completed_steps=list(chunk.completed_steps),
            step_timings=dict(chunk.step_timings),
            step_details=dict(chunk.step_details),
        )
        content_path = config.runtime.write_content(
            chunk.registration.lesson_id,
            content.model_dump(mode="python", exclude_none=True),
        )
        return PersistedContentArtifact(
            lesson_id=chunk.registration.lesson_id,
            created_at=created_at,
            content_path=content_path,
        )