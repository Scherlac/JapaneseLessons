from abc import ABC, abstractmethod

from ..models import GeneralItem, Sentence


class ItemGenerator(ABC):
    """Interface for converting LLM responses to GeneralItem/Sentence models."""
    @abstractmethod
    def convert_noun(self, llm_item: dict, base_item: GeneralItem) -> GeneralItem:
        """Enrich base_item with LLM-generated content (examples, memory tips)."""
        pass

    @abstractmethod
    def convert_verb(self, llm_item: dict, base_item: GeneralItem) -> GeneralItem:
        """Enrich base_item with LLM-generated content (conjugations, memory tips)."""
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
