from __future__ import annotations

from .action import RegisterLessonAction, RegisterLessonRequest
from ..pipeline_core import ActionStep, LessonContext, LessonPlan, LessonRegistrationArtifact


class RegisterLessonStep(ActionStep[LessonPlan, LessonRegistrationArtifact]):
    """Step 7 — Register and complete the lesson in curriculum.json."""

    name = "register_lesson"
    description = "Add + complete the lesson in curriculum.json"
    _action = RegisterLessonAction()

    @property
    def action(self) -> RegisterLessonAction:
        return self._action

    def should_skip(self, ctx: LessonContext) -> bool:
        return ctx.lesson_id is not None

    def build_input(self, ctx: LessonContext) -> LessonPlan:
        return ctx.lesson_plan
    
    def merge_output(self, ctx: LessonContext, outputs: LessonRegistrationArtifact) -> LessonContext:
        ctx.lesson_id = outputs.lesson_id
        ctx.created_at = outputs.created_at
        ctx.curriculum = outputs.curriculum
        self._log(ctx, f"       lesson_id={outputs.lesson_id}, created_at={outputs.created_at}")
        return ctx