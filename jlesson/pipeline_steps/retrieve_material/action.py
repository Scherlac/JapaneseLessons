from __future__ import annotations

from dataclasses import dataclass

from jlesson.models import Phase

from ..pipeline_core import ActionConfig, RetrievedMaterialArtifact, StepAction


@dataclass
class RetrieveMaterialRequest:
    """Composite request for lesson-material retrieval."""

    block_index: int
    theme: str
    requested_language: str
    filters: dict[str, str]
    limit: int


class RetrieveMaterialAction(StepAction[RetrieveMaterialRequest, RetrievedMaterialArtifact]):
    """Query retrieval, gate by coverage, and convert the result into typed lesson seed material."""

    @staticmethod
    def estimate_coverage(config, result) -> float:
        requested_total = max(config.num_nouns + config.num_verbs, 1)
        retrieved_total = min(len(result.material.nouns), config.num_nouns)
        retrieved_total += min(len(result.material.verbs), config.num_verbs)
        return retrieved_total / requested_total

    def run(
        self,
        config: ActionConfig,
        chunk: RetrieveMaterialRequest,
    ) -> RetrievedMaterialArtifact:
        result = config.runtime.query_retrieval(
            chunk.theme,
            requested_language=chunk.requested_language,
            filters=chunk.filters,
            limit=chunk.limit,
        )
        result.coverage = self.estimate_coverage(config.lesson, result)

        if result.coverage < config.lesson.retrieval_min_coverage:
            if not result.fallback_reason:
                result.fallback_reason = (
                    f"coverage {result.coverage:.0%} below minimum "
                    f"{config.lesson.retrieval_min_coverage:.0%}"
                )
            return RetrievedMaterialArtifact(
                vocab=None,
                nouns=[],
                verbs=[],
                noun_items=[],
                verb_items=[],
                sentences=[],
                selected_grammar=[],
                retrieval_result=result,
            )

        generator = config.language.generator
        nouns = [
            generator.convert_raw_noun(item)
            for item in result.material.nouns[: config.lesson.num_nouns]
        ]
        verbs = [
            generator.convert_raw_verb(item)
            for item in result.material.verbs[: config.lesson.num_verbs]
        ]
        noun_items = list(nouns)
        for item in noun_items:
            item.phase = Phase.NOUNS
        verb_items = list(verbs)
        for item in verb_items:
            item.phase = Phase.VERBS
        sentences = [
            generator.convert_sentence(item)
            for item in result.material.sentences
        ]
        for item in sentences:
            item.phase = Phase.GRAMMAR

        grammar_map = {
            grammar.id: grammar for grammar in config.language.grammar_progression
        }
        selected_grammar = [
            grammar_map[grammar_id]
            for grammar_id in result.material.grammar_ids
            if grammar_id in grammar_map
        ]
        result.used_retrieval = True
        return RetrievedMaterialArtifact(
            vocab=None,
            nouns=nouns,
            verbs=verbs,
            noun_items=noun_items,
            verb_items=verb_items,
            sentences=sentences,
            selected_grammar=selected_grammar,
            retrieval_result=result,
        )