from __future__ import annotations

from datetime import datetime, timezone

from jlesson.curriculum import add_lesson, complete_lesson, save_curriculum

from .runtime import lesson_pipeline_module


class RegisterLessonStep(lesson_pipeline_module().PipelineStep):
    """Step 7 — Register and complete the lesson in curriculum.json."""

    name = "register_lesson"
    description = "Add + complete the lesson in curriculum.json"

    def execute(self, ctx: lesson_pipeline_module().LessonContext) -> lesson_pipeline_module().LessonContext:
        pipeline = lesson_pipeline_module()
        lesson_number = len(ctx.curriculum.get("lessons", [])) + 1
        lesson = add_lesson(
            ctx.curriculum,
            title=f"Lesson {lesson_number}: {ctx.config.theme.title()}",
            theme=ctx.config.theme,
            nouns=ctx.nouns,
            verbs=ctx.verbs,
            grammar_ids=[pipeline.PipelineGadgets.grammar_id(g) for g in ctx.selected_grammar],
            items_count=len(ctx.noun_items) + len(ctx.sentences),
        )
        complete_lesson(ctx.curriculum, lesson["id"])
        ctx.lesson_id = lesson["id"]
        save_curriculum(ctx.curriculum, ctx.config.curriculum_path)
        ctx.created_at = (
            datetime.now(timezone.utc)
            .isoformat(timespec="seconds")
            .replace("+00:00", "Z")
        )
        grammar_ids = [pipeline.PipelineGadgets.grammar_id(g) for g in ctx.selected_grammar]
        ctx.report.add(
            "header",
            "\n".join(
                [
                    f"# Lesson {ctx.lesson_id}: {ctx.config.theme.title()}",
                    "",
                    f"> Generated: {ctx.created_at}",
                    f"> Grammar: {', '.join(grammar_ids) or '(none)'}",
                    "",
                ]
            ),
        )
        self._log(
            ctx, f"       lesson #{ctx.lesson_id} -> {ctx.config.curriculum_path}"
        )
        return ctx