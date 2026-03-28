from abc import ABC, abstractmethod

from ..models import GeneralItem, Sentence


class ItemGenerator(ABC):
    """Interface for converting LLM responses to GeneralItem/Sentence models."""

    def build_default_narrative(self, theme: str, lesson_number: int) -> str:
        """Build a default story context for sentence generation."""
        blocks = self.build_default_narrative_blocks(theme, lesson_number, 1)
        return blocks[0] if blocks else ""

    @abstractmethod
    def build_default_narrative_blocks(
        self,
        theme: str,
        lesson_number: int,
        block_count: int,
    ) -> list[str]:
        """Build a default narrative progression across lesson blocks."""
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
