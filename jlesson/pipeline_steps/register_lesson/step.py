from __future__ import annotations

from .action import RegisterLessonAction, RegisterLessonRequest
from ..pipeline_core import ActionStep, LessonContext, LessonRegistrationArtifact


class RegisterLessonStep(ActionStep[RegisterLessonRequest, LessonRegistrationArtifact]):
    """Step 7 — Register and complete the lesson in curriculum.json."""

    name = "register_lesson"
    description = "Add + complete the lesson in curriculum.json"
    _action = RegisterLessonAction()

    @property
    def action(self) -> RegisterLessonAction:
        return self._action

    def should_skip(self, ctx: LessonContext) -> bool:
        return ctx.lesson_id > 0

    def build_chunks(self, ctx: LessonContext) -> list[RegisterLessonRequest]:
        return [
            RegisterLessonRequest(
                theme=ctx.config.theme,
                nouns=[n.source.display_text for n in ctx.nouns],
                verbs=[v.source.display_text for v in ctx.verbs],
                grammar_ids=[g.id for g in ctx.selected_grammar],
                block_grammar_ids=[[g.id for g in block] for block in ctx.selected_grammar_blocks],
                items_count=len(ctx.noun_items) + len(ctx.sentences),
            )
        ]

    def merge_outputs(self, ctx: LessonContext, outputs: list[LessonRegistrationArtifact]) -> LessonContext:
        result = outputs[-1]
        ctx.lesson_id = result.lesson_id
        ctx.created_at = result.created_at
        ctx.curriculum = result.curriculum
        ctx.report.add("header", result.header_markdown)
        self._log(ctx, f"       lesson #{ctx.lesson_id} -> {ctx.config.curriculum_path}")
        return ctx