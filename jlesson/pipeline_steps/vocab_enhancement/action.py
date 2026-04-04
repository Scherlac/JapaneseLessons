from __future__ import annotations

from dataclasses import dataclass

from jlesson.models import GeneralItem

from ..pipeline_core import ActionConfig, VocabSet, StepAction, VocabEnhancementArtifact


@dataclass
class VocabEnhancementRequest(VocabSet):
    """Composite request for merged noun/verb vocab enrichment."""

    lesson_number: int
    enabled_parts: tuple[str, ...]


class VocabEnhancementAction(StepAction[VocabEnhancementRequest, VocabEnhancementArtifact]):
    """Enrich selected nouns and verbs through one shared step boundary."""

    NOUN_BATCH_SIZE = 25
    VERB_BATCH_SIZE = 20

    def run(self, config: ActionConfig, chunk: VocabEnhancementRequest) -> VocabEnhancementArtifact:
        return VocabEnhancementArtifact(
            vocab=chunk.vocab,
            nouns=chunk.nouns,
            verbs=chunk.verbs,
            noun_items=self._enrich_nouns(config, chunk),
            verb_items=self._enrich_verbs(config, chunk),
        )

    def _enrich_nouns(self, config: ActionConfig, chunk: VocabEnhancementRequest) -> list[GeneralItem]:
        if "nouns" not in chunk.enabled_parts:
            return []
        enriched: list[GeneralItem] = []
        for batch in self._chunk(chunk.nouns, self.NOUN_BATCH_SIZE):
            prompt = config.language.prompts.build_noun_practice_prompt(batch, chunk.lesson_number)
            result = config.runtime.call_llm(prompt)
            raw_items = result.get("noun_items", [])
            enriched.extend(
                config.language.generator.convert_noun(raw, base)
                for raw, base in zip(raw_items, batch)
            )
        return enriched if enriched else list(chunk.nouns)

    def _enrich_verbs(self, config: ActionConfig, chunk: VocabEnhancementRequest) -> list[GeneralItem]:
        if "verbs" not in chunk.enabled_parts:
            return []
        enriched: list[GeneralItem] = []
        for batch in self._chunk(chunk.verbs, self.VERB_BATCH_SIZE):
            prompt = config.language.prompts.build_verb_practice_prompt(batch, chunk.lesson_number)
            result = config.runtime.call_llm(prompt)
            raw_items = result.get("verb_items", [])
            enriched.extend(
                config.language.generator.convert_verb(raw, base)
                for raw, base in zip(raw_items, batch)
            )
        return enriched if enriched else list(chunk.verbs)

    @staticmethod
    def _chunk(items: list[GeneralItem], size: int) -> list[list[GeneralItem]]:
        if not items:
            return []
        return [items[index : index + size] for index in range(0, len(items), size)]