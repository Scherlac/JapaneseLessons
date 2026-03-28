from ..models import GeneralItem, PartialItem, Sentence
from ._base import ItemGenerator


class EngJapItemGenerator(ItemGenerator):
    """Item generator for English-Japanese lessons."""

    def build_default_narrative_blocks(
        self,
        theme: str,
        lesson_number: int,
        block_count: int,
    ) -> list[str]:
        return [
            (
                f"Lesson {lesson_number}, block {block_index}, stays in the world of '{theme}'. "
                "Start with simple observation and identity sentences, then move into small concrete actions. "
                "Keep the tone warm, clear, and beginner friendly, while advancing the situation from the previous block."
            )
            for block_index in range(1, block_count + 1)
        ]

    def convert_noun(self, llm_item: dict, base_item: GeneralItem) -> GeneralItem:
        return GeneralItem(
            source=PartialItem(
                display_text=base_item.source.display_text,
                extra={**base_item.source.extra, "example_sentence_en": llm_item.get("example_sentence_en", "")},
            ),
            target=PartialItem(
                display_text=base_item.target.display_text,
                pronunciation=base_item.target.pronunciation,
                extra={
                    **base_item.target.extra,
                    "example_sentence_jp": llm_item.get("example_sentence_jp", ""),
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
                    "memory_tip": llm_item.get("memory_tip", ""),
                    "polite_forms": llm_item.get("polite_forms", {}),
                },
            ),
        )

    def convert_sentence(self, llm_item: dict) -> Sentence:
        return Sentence(
            source=PartialItem(display_text=llm_item["english"]),
            target=PartialItem(display_text=llm_item["japanese"], pronunciation=llm_item["romaji"]),
            grammar_id=llm_item.get("grammar_id", ""),
            grammar_parameters={"person": llm_item.get("person", "")}
        )

    def convert_raw_noun(self, source_item: dict) -> GeneralItem:
        return GeneralItem(
            source=PartialItem(display_text=source_item["english"]),
            target=PartialItem(
                display_text=source_item.get("japanese", ""),
                pronunciation=source_item.get("romaji", ""),
                extra={"kanji": source_item.get("kanji", "")},
            ),
        )

    def convert_raw_verb(self, source_item: dict) -> GeneralItem:
        return GeneralItem(
            source=PartialItem(display_text=source_item["english"]),
            target=PartialItem(
                display_text=source_item.get("japanese", ""),
                pronunciation=source_item.get("romaji", ""),
                extra={
                    "kanji": source_item.get("kanji", ""),
                    "type": source_item.get("type", ""),
                    "masu_form": source_item.get("masu_form", ""),
                },
            ),
        )
