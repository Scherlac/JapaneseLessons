from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from jlesson.lesson_pipeline.pipeline_paths import resolve_vocab_dir
from jlesson.lesson_store import save_shared_vocab
from jlesson.models import GeneralItem, LessonContent, Sentence

from ..pipeline_core import (
    ActionConfig,
    LessonRegistrationArtifact,
    PersistedContentArtifact,
    StepAction,
)


def _item_to_vocab_dict(item: GeneralItem | dict) -> dict:
    if isinstance(item, dict):
        return item
    source_text = item.source.display_text or ""
    payload = {**item.source.extra, **item.target.extra}
    payload["id"] = source_text.strip().lower()
    payload["source"] = source_text
    payload["target"] = item.target.display_text or ""
    payload["phonetic"] = item.target.pronunciation or ""
    return payload


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

    def __post_init__(self):
        if self.completed_steps is None:
            self.completed_steps = []
        if self.step_timings is None:
            self.step_timings = {}


class PersistContentAction(StepAction[PersistContentRequest, PersistedContentArtifact]):
    """Persist lesson content and shared vocab using the typed registration artifact."""

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
            completed_steps=list(chunk.completed_steps),
            step_timings=dict(chunk.step_timings),
        )
        content_path = config.runtime.write_content(
            chunk.registration.lesson_id,
            content.model_dump(mode="python", exclude_none=True),
        )
        vocab_path = save_shared_vocab(
            resolve_vocab_dir(config.lesson),
            chunk.theme,
            [_item_to_vocab_dict(item) for item in chunk.noun_items],
            [_item_to_vocab_dict(item) for item in chunk.verb_items],
        )
        return PersistedContentArtifact(
            lesson_id=chunk.registration.lesson_id,
            created_at=created_at,
            content_path=content_path,
            vocab_path=vocab_path,
        )