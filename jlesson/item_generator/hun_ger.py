from ..models import CanonicalItem, GeneralItem, PartialItem, Sentence
from ._base import ItemGenerator


class HunGerItemGenerator(ItemGenerator):
    """Item generator for Hungarian-German lessons.

    Canonical text is preserved as the English term (narrative language)
    to support cross-language retrieval and branch linking.
    """

    def convert_noun(self, llm_item: dict, base_item: GeneralItem) -> GeneralItem:
        canonical = llm_item.get("english", "") or base_item.canonical.text
        return GeneralItem(
            id=base_item.id,
            canonical=CanonicalItem(text=canonical, concept_type="noun"),
            source=PartialItem(
                display_text=base_item.source.display_text,
                extra={
                    **base_item.source.extra,
                    "example_sentence_hu": llm_item.get("example_sentence_hu", ""),
                },
            ),
            target=PartialItem(
                display_text=base_item.target.display_text,
                pronunciation=base_item.target.pronunciation,
                extra={
                    **base_item.target.extra,
                    "article": llm_item.get("article", base_item.target.extra.get("article", "")),
                    "example_sentence_de": llm_item.get("example_sentence_de", ""),
                    "memory_tip": llm_item.get("memory_tip", ""),
                },
            ),
        )

    def convert_verb(self, llm_item: dict, base_item: GeneralItem) -> GeneralItem:
        canonical = llm_item.get("english", "") or base_item.canonical.text
        return GeneralItem(
            id=base_item.id,
            canonical=CanonicalItem(text=canonical, concept_type="verb"),
            source=PartialItem(
                display_text=base_item.source.display_text,
                extra=base_item.source.extra,
            ),
            target=PartialItem(
                display_text=base_item.target.display_text,
                pronunciation=base_item.target.pronunciation,
                extra={
                    **base_item.target.extra,
                    "partizip_ii": llm_item.get("partizip_ii", base_item.target.extra.get("partizip_ii", "")),
                    "hilfsverb": llm_item.get("hilfsverb", base_item.target.extra.get("hilfsverb", "haben")),
                    "example_sentence_de": llm_item.get("example_sentence_de", ""),
                    "memory_tip": llm_item.get("memory_tip", ""),
                },
            ),
        )

    def convert_sentence(self, llm_item: dict) -> Sentence:
        return Sentence(
            canonical=CanonicalItem(text=llm_item.get("english", ""), concept_type="sentence"),
            source=PartialItem(display_text=llm_item.get("hungarian", "")),
            target=PartialItem(
                display_text=llm_item.get("german", ""),
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
            source=PartialItem(display_text=source_item.get("hungarian", "")),
            target=PartialItem(
                display_text=source_item.get("german", ""),
                pronunciation=source_item.get("pronunciation", ""),
                extra={"article": source_item.get("article", "")},
            ),
        )

    def convert_raw_verb(self, source_item: dict) -> GeneralItem:
        english = source_item.get("english", "")
        return GeneralItem(
            id=english.strip().lower(),
            canonical=CanonicalItem(text=english, concept_type="verb"),
            source=PartialItem(display_text=source_item.get("hungarian", "")),
            target=PartialItem(
                display_text=source_item.get("german", ""),
                pronunciation=source_item.get("pronunciation", ""),
                extra={
                    "partizip_ii": source_item.get("partizip_ii", ""),
                    "hilfsverb": source_item.get("hilfsverb", "haben"),
                },
            ),
        )
