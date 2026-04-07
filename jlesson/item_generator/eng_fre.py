"""Item generator for the English → French language pair."""

from __future__ import annotations

from ..models import CanonicalItem, GeneralItem, PartialItem, Sentence
from ._base import ItemGenerator


class EngFrItemGenerator(ItemGenerator):
    """Item generator for English-French lessons."""

    def convert_noun(self, llm_item: dict, base_item: GeneralItem) -> GeneralItem:
        return GeneralItem(
            source=PartialItem(
                display_text=base_item.source.display_text,
                extra={
                    **base_item.source.extra,
                    "example_sentence_en": llm_item.get("example_sentence_en", ""),
                },
            ),
            target=PartialItem(
                display_text=base_item.target.display_text,
                pronunciation=base_item.target.pronunciation,
                extra={
                    **base_item.target.extra,
                    "article": llm_item.get("article", base_item.target.extra.get("article", "")),
                    "example_sentence_fr": llm_item.get("example_sentence_fr", ""),
                    "memory_tip": llm_item.get("memory_tip", ""),
                },
            ),
        )

    def convert_verb(self, llm_item: dict, base_item: GeneralItem) -> GeneralItem:
        return GeneralItem(
            source=PartialItem(display_text=base_item.source.display_text),
            target=PartialItem(
                display_text=base_item.target.display_text,
                pronunciation=base_item.target.pronunciation,
                extra={
                    **base_item.target.extra,
                    "past_participle": llm_item.get(
                        "past_participle", base_item.target.extra.get("past_participle", "")
                    ),
                    "auxiliary": llm_item.get(
                        "auxiliary", base_item.target.extra.get("auxiliary", "avoir")
                    ),
                    "memory_tip": llm_item.get("memory_tip", ""),
                },
            ),
        )

    def convert_sentence(self, llm_item: dict) -> Sentence:
        return Sentence(
            source=PartialItem(display_text=llm_item.get("english", "")),
            target=PartialItem(
                display_text=llm_item.get("french", ""),
                pronunciation=llm_item.get("pronunciation", ""),
            ),
            grammar_id=llm_item.get("grammar_id", ""),
            grammar_parameters={"person": llm_item.get("person", "")},
        )

    def convert_raw_noun(self, source_item: dict) -> GeneralItem:
        english = source_item.get("english", "")
        return GeneralItem(
            id=english.strip().lower(),
            canonical=CanonicalItem(text=english, concept_type="noun"),
            source=PartialItem(display_text=english),
            target=PartialItem(
                display_text=source_item.get("french", ""),
                pronunciation=source_item.get("pronunciation", ""),
                extra={
                    "article": source_item.get("article", ""),
                },
            ),
        )

    def convert_raw_verb(self, source_item: dict) -> GeneralItem:
        english = source_item.get("english", "")
        return GeneralItem(
            id=english.strip().lower(),
            canonical=CanonicalItem(text=english, concept_type="verb"),
            source=PartialItem(display_text=english),
            target=PartialItem(
                display_text=source_item.get("french", ""),
                pronunciation=source_item.get("pronunciation", ""),
                extra={
                    "past_participle": source_item.get("past_participle", ""),
                    "auxiliary": source_item.get("auxiliary", "avoir"),
                },
            ),
        )
