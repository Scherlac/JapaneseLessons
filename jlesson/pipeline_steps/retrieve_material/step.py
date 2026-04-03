from __future__ import annotations

from .action import RetrieveMaterialAction, RetrieveMaterialRequest
from ..pipeline_core import (
    ActionStep,
    CanonicalVocabSelection,
    LessonConfig,
    LessonContext,
    LessonOutline,
    RetrievedMaterialArtifact,
)


class RetrieveLessonMaterialStep(ActionStep[RetrieveMaterialRequest, RetrievedMaterialArtifact]):
    """Step 1 — Optional retrieval before the current generation flow."""

    name = "retrieve_material"
    description = "Retrieve reusable lesson material with safe fallback"
    _action = RetrieveMaterialAction()

    @property
    def action(self) -> RetrieveMaterialAction:
        return self._action

    def should_skip(self, ctx: LessonContext) -> bool:
        return ctx.retrieval_result is not None

    @staticmethod
    def _get_target_language_code(ctx: LessonContext) -> str:
        return ctx.language_config.target.display_name.lower()

    @staticmethod
    def _render_retrieval_trace(result) -> str:
        lines = [
            "## Retrieval Trace",
            "",
            f"> Query: `{result.query}`",
            f"> Requested language: `{result.requested_language}`",
            f"> Coverage: {result.coverage:.0%}",
        ]
        if result.filters:
            filters = ", ".join(
                f"{key}={value}" for key, value in sorted(result.filters.items())
            )
            lines.append(f"> Filters: `{filters}`")
        if result.used_retrieval:
            lines.append("> Outcome: used retrieved material")
        elif result.fallback_reason:
            lines.append(f"> Fallback: {result.fallback_reason}")
        else:
            lines.append(
                "> Outcome: retrieval produced candidates but coverage was insufficient"
            )
        lines.extend(["", "| # | Type | Canonical | Score |", "|---|------|-----------|-------|"])
        for index, candidate in enumerate(result.candidates[:5], 1):
            lines.append(
                f"| {index} | {candidate.concept_type} | {candidate.canonical_text_en} | {candidate.score:.1f} |"
            )
        if not result.candidates:
            lines.append("| - | - | no candidates | 0.0 |")
        lines.append("")
        return "\n".join(lines)

    def build_chunks(self, ctx: LessonContext) -> list[RetrieveMaterialRequest]:
        return [
            RetrieveMaterialRequest(
                block_index=0,
                theme=ctx.config.theme,
                requested_language=self._get_target_language_code(ctx),
                filters={"theme": ctx.config.theme},
                limit=ctx.config.retrieval_limit,
            )
        ]

    def merge_outputs(
        self,
        ctx: LessonContext,
        outputs: list[RetrievedMaterialArtifact],
    ) -> LessonContext:
        result = outputs[-1]
        if result.retrieval_result.used_retrieval:
            ctx.nouns = result.nouns
            ctx.verbs = result.verbs
            ctx.noun_items = result.noun_items
            ctx.verb_items = result.verb_items
            ctx.sentences = result.sentences
            ctx.selected_grammar = result.selected_grammar
            ctx.selected_grammar_blocks = result.selected_grammar_blocks
            # Mark canonical planning as satisfied so planner/grammar-select guards pass.
            if ctx.canonical_vocab is None:
                ctx.canonical_vocab = CanonicalVocabSelection(
                    nouns=[],
                    verbs=[],
                )
            if ctx.lesson_outline is None:
                ctx.lesson_outline = LessonOutline(
                    blocks=[],
                    grammar_ids=[g.id for g in ctx.selected_grammar],
                )
            self._log(
                ctx,
                "       hit : "
                f"{len(ctx.nouns)} nouns, {len(ctx.verbs)} verbs, {len(ctx.sentences)} sentences",
            )
        elif result.retrieval_result.fallback_reason:
            self._log(ctx, f"       fallback : {result.retrieval_result.fallback_reason}")

        ctx.retrieval_result = result.retrieval_result
        ctx.report.add("retrieval", self._render_retrieval_trace(result.retrieval_result))
        return ctx