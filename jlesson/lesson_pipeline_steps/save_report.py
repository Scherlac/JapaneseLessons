from __future__ import annotations

from jlesson.lesson_report import save_report
from jlesson.profiles import get_profile
from jlesson.touch_compiler import count_touches

from jlesson.models import Phase

from .runtime import lesson_pipeline_module


class SaveReportStep(lesson_pipeline_module().PipelineStep):
    """Step 12 — Finalize and save Markdown lesson report."""

    name = "save_report"
    description = "Finalize and save Markdown lesson report"

    def execute(self, ctx: lesson_pipeline_module().LessonContext) -> lesson_pipeline_module().LessonContext:
        ctx.report.add("summary", self._summary(ctx))
        report = ctx.report.render()
        output_dir = lesson_pipeline_module().PipelineGadgets.resolve_output_dir(ctx.config)
        report_path = output_dir / f"lesson_{ctx.lesson_id:03d}" / "report.md"
        ctx.report_path = save_report(report, report_path)
        self._log(ctx, f"       {ctx.report_path}")
        return ctx

    @staticmethod
    def _summary(ctx: lesson_pipeline_module().LessonContext) -> str:
        n_nouns = len(ctx.noun_items)
        n_verbs = len(ctx.verb_items)
        n_sentences = len(ctx.sentences)
        total = n_nouns + n_verbs + n_sentences
        profile = get_profile(ctx.config.profile)
        counts = count_touches(n_nouns, n_verbs, n_sentences, profile)
        noun_reps = len(profile.cycle_for(Phase.NOUNS))
        verb_reps = len(profile.cycle_for(Phase.VERBS))
        grammar_reps = len(profile.cycle_for(Phase.GRAMMAR))
        lines = [
            "## Summary",
            "",
            f"> Profile: **{ctx.config.profile}**",
            "",
            "| Phase | Items | Repetitions | Touches |",
            "|-------|-------|-------------|---------|",
            f"| Nouns | {n_nouns} | {noun_reps} | {counts['nouns']} |",
            f"| Verbs | {n_verbs} | {verb_reps} | {counts['verbs']} |",
            f"| Grammar | {n_sentences} | {grammar_reps} | {counts['grammar']} |",
            f"| **Total** | **{total}** | | **{counts['total']}** |",
            "",
        ]
        return "\n".join(lines)