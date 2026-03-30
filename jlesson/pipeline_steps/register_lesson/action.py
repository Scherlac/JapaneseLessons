from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from jlesson.curriculum import add_lesson, complete_lesson

from ..pipeline_core import ActionConfig, LessonRegistrationArtifact, StepAction, VocabEnhancementArtifact


@dataclass
class RegisterLessonRequest(VocabEnhancementArtifact):
    """Composite storage request for lesson registration."""

    theme: str
    grammar_ids: list[str]
    block_grammar_ids: list[list[str]]
    items_count: int


class RegisterLessonAction(StepAction[RegisterLessonRequest, LessonRegistrationArtifact]):
    """Register a lesson in the curriculum and return the typed registration artifact."""

    def run(self, config: ActionConfig, chunk: RegisterLessonRequest) -> LessonRegistrationArtifact:
        curriculum = config.curriculum.model_copy(deep=True)
        lesson_number = len(curriculum.lessons) + 1
        lesson = add_lesson(
            curriculum,
            title=f"Lesson {lesson_number}: {chunk.theme.title()}",
            theme=chunk.theme,
            nouns=[item.source.display_text for item in chunk.nouns],
            verbs=[item.source.display_text for item in chunk.verbs],
            grammar_ids=chunk.grammar_ids,
            items_count=chunk.items_count,
        )
        complete_lesson(curriculum, lesson.id)
        config.runtime.write_curriculum(curriculum)

        created_at = (
            datetime.now(timezone.utc)
            .isoformat(timespec="seconds")
            .replace("+00:00", "Z")
        )
        block_grammar_lines = []
        for index, grammar_block in enumerate(chunk.block_grammar_ids, 1):
            ids = ", ".join(grammar_block) or "(none)"
            block_grammar_lines.append(f"> Block {index} grammar: {ids}")

        header_markdown = "\n".join(
            [
                f"# Lesson {lesson.id}: {chunk.theme.title()}",
                "",
                f"> Generated: {created_at}",
                f"> Grammar: {', '.join(chunk.grammar_ids) or '(none)'}",
                *block_grammar_lines,
                "",
            ]
        )
        return LessonRegistrationArtifact(
            lesson_id=lesson.id,
            created_at=created_at,
            curriculum=curriculum,
            header_markdown=header_markdown,
        )