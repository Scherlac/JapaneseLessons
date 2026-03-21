from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from jlesson.retrieval import get_retrieval_service

from .runtime import lesson_pipeline_module

if TYPE_CHECKING:
    from jlesson.lesson_pipeline import LessonConfig, LessonContext


class RetrieveLessonMaterialStep(lesson_pipeline_module().PipelineStep):
    """Step 1 — Optional retrieval before the current generation flow."""

    name = "retrieve_material"
    description = "Retrieve reusable lesson material with safe fallback"

    @staticmethod
    def _resolve_retrieval_store_path(config: LessonConfig) -> Path:
        if config.retrieval_store_path is not None:
            return Path(config.retrieval_store_path)
        return Path(__file__).parent.parent.parent / "output" / "retrieval" / "material_index.json"

    @staticmethod
    def _get_non_english_branch_language(ctx: LessonContext) -> str:
        native = ctx.language_config.native_language.lower()
        target = ctx.language_config.target_language.lower()
        if native != "english":
            return native
        return target

    @staticmethod
    def _estimate_retrieval_coverage(
        ctx: LessonContext,
        result,
    ) -> float:
        requested_total = max(ctx.config.num_nouns + ctx.config.num_verbs, 1)
        retrieved_total = min(len(result.material.nouns), ctx.config.num_nouns)
        retrieved_total += min(len(result.material.verbs), ctx.config.num_verbs)
        return retrieved_total / requested_total

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

    def execute(self, ctx: LessonContext) -> LessonContext:
        service = get_retrieval_service(
            ctx.config.retrieval_enabled,
            self._resolve_retrieval_store_path(ctx.config),
            backend=ctx.config.retrieval_backend,
            embedding_model=ctx.config.retrieval_embedding_model,
        )
        result = service.search(
            ctx.config.theme,
            requested_language=self._get_non_english_branch_language(ctx),
            filters={"theme": ctx.config.theme},
            limit=ctx.config.retrieval_limit,
        )
        result.coverage = self._estimate_retrieval_coverage(ctx, result)
        if result.coverage < ctx.config.retrieval_min_coverage:
            if not result.fallback_reason:
                result.fallback_reason = (
                    f"coverage {result.coverage:.0%} below minimum "
                    f"{ctx.config.retrieval_min_coverage:.0%}"
                )
            self._log(ctx, f"       fallback : {result.fallback_reason}")
        else:
            ctx.nouns = result.material.nouns[: ctx.config.num_nouns]
            ctx.verbs = result.material.verbs[: ctx.config.num_verbs]
            ctx.noun_items = [
                ctx.language_config.generator.convert_raw_noun(item)
                for item in ctx.nouns
            ]
            for item in ctx.noun_items:
                item.item_type = "noun"
            ctx.verb_items = [
                ctx.language_config.generator.convert_raw_verb(item)
                for item in ctx.verbs
            ]
            for item in ctx.verb_items:
                item.item_type = "verb"
            ctx.sentences = [
                ctx.language_config.generator.convert_sentence(item)
                for item in result.material.sentences
            ]
            grammar_map = {
                grammar.id: grammar for grammar in ctx.language_config.grammar_progression
            }
            ctx.selected_grammar = [
                grammar_map[grammar_id].model_dump()
                for grammar_id in result.material.grammar_ids
                if grammar_id in grammar_map
            ]
            result.used_retrieval = True
            self._log(
                ctx,
                "       hit : "
                f"{len(ctx.nouns)} nouns, {len(ctx.verbs)} verbs, {len(ctx.sentences)} sentences",
            )
        ctx.retrieval_result = result
        ctx.report.add("retrieval", self._render_retrieval_trace(result))
        return ctx