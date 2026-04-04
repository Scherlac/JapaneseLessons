from __future__ import annotations

from pydantic.v1 import BaseModel

from .action import RegisterLessonAction, RegisterLessonRequest
from ..pipeline_core import ActionStep, LessonContext, LessonPlan, LessonRegistrationArtifact


class RegisterLessonStep(ActionStep[LessonPlan, BaseModel]):
    """Step 7 — Register and complete the lesson in curriculum.json."""

    name = "register_lesson"
    description = "Add + complete the lesson in curriculum.json"
    _action = RegisterLessonAction()

    @property
    def action(self) -> RegisterLessonAction:
        return self._action

    def should_skip(self, ctx: LessonContext) -> bool:
        if ctx.lesson_plan is None:
            return False
        return True

    def build_input(self, ctx: LessonContext) -> LessonPlan:
        return ctx.lesson_plan
    
    def merge_output(self, ctx: LessonContext, outputs: BaseModel) -> LessonContext:
        return ctx