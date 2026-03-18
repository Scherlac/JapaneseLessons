from abc import ABC, abstractmethod

from .models import GeneralItem, PartialItem, Sentence


class ItemGenerator(ABC):
    """Interface for converting LLM responses to GeneralItem/Sentence models."""

    @abstractmethod
    def build_default_narrative(self, theme: str, lesson_number: int) -> str:
        """Build a default story context for sentence generation."""
        pass

    @abstractmethod
    def convert_noun(self, llm_item: dict, source_item: dict) -> GeneralItem:
        """Convert LLM noun response to GeneralItem."""
        pass

    @abstractmethod
    def convert_verb(self, llm_item: dict, source_item: dict) -> GeneralItem:
        """Convert LLM verb response to GeneralItem."""
        pass

    @abstractmethod
    def convert_sentence(self, llm_item: dict) -> Sentence:
        """Convert LLM sentence response to Sentence."""
        pass

    @abstractmethod
    def convert_raw_noun(self, source_item: dict) -> GeneralItem:
        """Convert raw vocab noun to GeneralItem (fallback)."""
        pass

    @abstractmethod
    def convert_raw_verb(self, source_item: dict) -> GeneralItem:
        """Convert raw vocab verb to GeneralItem (fallback)."""
        pass


class EngJapItemGenerator(ItemGenerator):
    """Item generator for English-Japanese lessons."""

    def build_default_narrative(self, theme: str, lesson_number: int) -> str:
        return (
            f"Lesson {lesson_number} begins in the world of '{theme}'. "
            "Introduce Kiki, her broom, her cat Jiji, and her new town. "
            "Start with simple observation and identity sentences, then add "
            "small daily actions in her environment. Keep the tone warm, clear, "
            "and beginner friendly."
        )

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
            target=PartialItem(display_text=source_item["japanese"], pronunciation=source_item["romaji"])
        )

    def convert_raw_verb(self, source_item: dict) -> GeneralItem:
        return GeneralItem(
            source=PartialItem(display_text=source_item["english"]),
            target=PartialItem(display_text=source_item["japanese"], pronunciation=source_item["romaji"], extra={"masu_form": source_item.get("masu_form", "")})
        )


class HunEngItemGenerator(ItemGenerator):
    """Item generator for Hungarian-English lessons."""

    def build_default_narrative(self, theme: str, lesson_number: int) -> str:
        return (
            f"Lesson {lesson_number} story context for theme '{theme}': "
            "start with who the main character is and where they are, then "
            "describe simple daily actions in that setting. Keep it suitable "
            "for beginner learners."
        )

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
            target=PartialItem(display_text=llm_item["english"], pronunciation=llm_item.get("pronunciation", "")),
            grammar_id=llm_item.get("grammar_id", ""),
            grammar_parameters={"person": llm_item.get("person", "")}
        )

    def convert_raw_noun(self, source_item: dict) -> GeneralItem:
        return GeneralItem(
            source=PartialItem(display_text=source_item.get("hungarian", "")),
            target=PartialItem(display_text=source_item["english"], pronunciation=source_item.get("pronunciation", ""))
        )

    def convert_raw_verb(self, source_item: dict) -> GeneralItem:
        return GeneralItem(
            source=PartialItem(display_text=source_item.get("hungarian", "")),
            target=PartialItem(display_text=source_item["english"], pronunciation=source_item.get("pronunciation", ""), extra={"past_tense": source_item.get("past_tense", "")})
        )