from ..models import GeneralItem, PartialItem, Sentence
from ._base import ItemGenerator


class HunEngItemGenerator(ItemGenerator):
    """Item generator for Hungarian-English lessons."""

    def build_default_narrative_blocks(
        self,
        theme: str,
        lesson_number: int,
        block_count: int,
    ) -> list[str]:
        return [
            (
                f"Lesson {lesson_number}, block {block_index}, uses the theme '{theme}'. "
                "Start with who the character is and where they are, then describe simple daily actions in that setting. "
                "Keep it suitable for beginner learners and let each block move the mini-story forward."
            )
            for block_index in range(1, block_count + 1)
        ]

    def convert_noun(self, llm_item: dict, source_item: dict) -> GeneralItem:
        n_item = {**source_item, **llm_item}
        return GeneralItem(
            source=PartialItem(
                display_text=n_item.get("hungarian", ""),
                extra={"example_sentence_hu": n_item.get("example_sentence_hu", "")}
            ),
            target=PartialItem(
                display_text=n_item["english"],
                pronunciation=n_item.get("pronunciation", ""),
                extra={
                    "example_sentence_en": n_item.get("example_sentence_en", ""),
                    "memory_tip": n_item.get("memory_tip", "")
                }
            )
        )

    def convert_verb(self, llm_item: dict, source_item: dict) -> GeneralItem:
        v_item = {**source_item, **llm_item}
        return GeneralItem(
            source=PartialItem(display_text=v_item.get("hungarian", "")),
            target=PartialItem(
                display_text=v_item.get("english", ""),
                pronunciation=v_item.get("pronunciation", ""),
                extra={"past_tense": v_item.get("past_tense", "")}
            )
        )

    def convert_sentence(self, llm_item: dict) -> Sentence:
        return Sentence(
            source=PartialItem(display_text=llm_item.get("hungarian", "")),
            target=PartialItem(
                display_text=llm_item["english"],
                pronunciation=llm_item.get("pronunciation", "")
            ),
            grammar_id=llm_item.get("grammar_id", ""),
            grammar_parameters={"person": llm_item.get("person", "")}
        )

    def convert_raw_noun(self, source_item: dict) -> GeneralItem:
        return GeneralItem(
            source=PartialItem(display_text=source_item.get("hungarian", "")),
            target=PartialItem(
                display_text=source_item["english"],
                pronunciation=source_item.get("pronunciation", "")
            )
        )

    def convert_raw_verb(self, source_item: dict) -> GeneralItem:
        return GeneralItem(
            source=PartialItem(display_text=source_item.get("hungarian", "")),
            target=PartialItem(
                display_text=source_item["english"],
                pronunciation=source_item.get("pronunciation", ""),
                extra={"past_tense": source_item.get("past_tense", "")}
            )
        )
