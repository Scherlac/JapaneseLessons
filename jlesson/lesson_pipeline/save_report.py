from __future__ import annotations

from jlesson.lesson_report import save_report
from .pipeline_core import LessonContext, PipelineStep
from .pipeline_paths import resolve_output_dir
from jlesson.profiles import get_profile
from jlesson.touch_compiler import count_touches

from jlesson.models import Phase


class SaveReportStep(PipelineStep):
    """Step 12 — Finalize and save Markdown lesson report."""

    name = "save_report"
    description = "Finalize and save Markdown lesson report"

    def execute(self, ctx: LessonContext) -> LessonContext:
        ctx.report.add("summary", self._summary(ctx))
        report = ctx.report.render()
        output_dir = resolve_output_dir(ctx.config)
        report_path = output_dir / f"lesson_{ctx.lesson_id:03d}" / "report.md"
        ctx.report_path = save_report(report, report_path)
        self._log(ctx, f"       {ctx.report_path}")
        return ctx

    @staticmethod
    def _summary(ctx: LessonContext) -> str:
        n_nouns = len(ctx.noun_items)
        n_verbs = len(ctx.verb_items)
        n_sentences = len(ctx.sentences)
        total = n_nouns + n_verbs + n_sentences
        profile = get_profile(ctx.config.profile)
        counts = count_touches(n_nouns, n_verbs, n_sentences, profile)
        noun_reps = len(profile.cycle_for(Phase.NOUNS))
        verb_reps = len(profile.cycle_for(Phase.VERBS))
        grammar_reps = len(profile.cycle_for(Phase.GRAMMAR))
        blocks = max(1, ctx.config.lesson_blocks)
        nouns_per_block = n_nouns // blocks if blocks else n_nouns
        verbs_per_block = n_verbs // blocks if blocks else n_verbs
        sentences_per_block = n_sentences // blocks if blocks else n_sentences
        lines = [
            "## Summary",
            "",
            f"> Profile: **{ctx.config.profile}**",
            f"> Blocks: **{ctx.config.lesson_blocks}**",
            "",
            "| Phase | Items per block | Total items | Repetitions | Total touches |",
            "|-------|-----------------|-------------|-------------|---------------|",
            f"| Nouns | {nouns_per_block} | {n_nouns} | {noun_reps} | {counts['nouns']} |",
            f"| Verbs | {verbs_per_block} | {n_verbs} | {verb_reps} | {counts['verbs']} |",
            f"| Grammar | {sentences_per_block} | {n_sentences} | {grammar_reps} | {counts['grammar']} |",
            f"| **Total** | **{nouns_per_block + verbs_per_block + sentences_per_block}** | **{total}** | | **{counts['total']}** |",
            "",
        ]
        return "\n".join(lines)