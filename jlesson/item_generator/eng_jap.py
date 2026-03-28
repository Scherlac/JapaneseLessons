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

    def convert_noun(self, llm_item: dict, source_item: dict) -> GeneralItem:
        n_item = {**source_item, **llm_item}  # Merge source with LLM overrides
        return GeneralItem(
            source=PartialItem(
                display_text=n_item["english"],
                extra={"example_sentence_en": n_item.get("example_sentence_en", "")}
            ),
            target=PartialItem(
                display_text=n_item["japanese"],
                pronunciation=n_item["romaji"],
                extra={
                    "kanji": n_item.get("kanji", ""),
                    "example_sentence_jp": n_item.get("example_sentence_jp", ""),
                    "memory_tip": n_item.get("memory_tip", "")
                }
            )
        )

    def convert_verb(self, llm_item: dict, source_item: dict) -> GeneralItem:
        v_item = {**source_item, **llm_item}
        return GeneralItem(
            source=PartialItem(display_text=v_item["english"]),
            target=PartialItem(
                display_text=v_item["japanese"],
                pronunciation=v_item["romaji"],
                extra={
                    "masu_form": v_item.get("masu_form", ""),
                    "kanji": v_item.get("kanji", "")
                }
            )
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
