from __future__ import annotations

from jlesson.lesson_pipeline.pipeline_paths import resolve_lesson_dir
from jlesson.models import Phase
from jlesson.profiles import get_profile
from jlesson.touch_compiler import count_touches

from .action import SaveReportAction, SaveReportRequest
from ..pipeline_core import ActionStep, LessonContext, RenderedVideoArtifact, ReportArtifact


class SaveReportStep(ActionStep[SaveReportRequest, ReportArtifact]):
    """Step 12 — Finalize and save Markdown lesson report."""

    name = "save_report"
    description = "Finalize and save Markdown lesson report"
    _action = SaveReportAction()

    @property
    def action(self) -> SaveReportAction:
        return self._action

    def should_skip(self, ctx: LessonContext) -> bool:
        return bool(ctx.report_path)

    def build_input(self, ctx: LessonContext) -> list[SaveReportRequest]:
        lesson_dir = resolve_lesson_dir(ctx.config, ctx.lesson_id)
        rendered = RenderedVideoArtifact(
            video_path=ctx.video_path,
            clip_count=len(ctx.touches),
            cards_dir=(lesson_dir / "cards") if (lesson_dir / "cards").exists() else None,
            audio_dir=(lesson_dir / "audio") if (lesson_dir / "audio").exists() else None,
        )
        return [
            SaveReportRequest(
                video_path=rendered.video_path,
                clip_count=rendered.clip_count,
                cards_dir=rendered.cards_dir,
                audio_dir=rendered.audio_dir,
                report=ctx.report,
                report_path=lesson_dir / "report.md",
                summary_markdown=self._summary(ctx),
            )
        ]

    def merge_output(self, ctx: LessonContext, outputs: list[ReportArtifact]) -> LessonContext:
        result = outputs[-1] if outputs else ReportArtifact(report_path=None)
        ctx.saved_report = result
        ctx.report_path = result.report_path
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
            f"> Grammar points per lesson: **{ctx.config.grammar_points_per_lesson}**",
            f"> Grammar points per block: **{ctx.config.grammar_points_per_block}**",
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