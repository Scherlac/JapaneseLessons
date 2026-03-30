from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from jlesson.language_config import LanguageConfig


@dataclass(frozen=True)
class NarrativeGeneratorLanguageConfig:
    """Language-specific configuration used only by the narrative generator step."""

    default_block_builder: Callable[[str, str, int], list[str]]
    canonical_language: str | None = None
    source_language_label: str | None = None

    def __post_init__(self) -> None:
        language = self.canonical_language or self.source_language_label
        if not language:
            raise ValueError("NarrativeGeneratorLanguageConfig requires a language label")
        object.__setattr__(self, "canonical_language", language)
        object.__setattr__(self, "source_language_label", language)


# ---------------------------------------------------------------------------
# Language-specific default block text (no ItemGenerator dependency)
# ---------------------------------------------------------------------------

def fallback_default_blocks(theme: str, level_details: str, block_count: int) -> list[str]:
    return [
        (
            f"Block {block_index}, stays in the world of '{theme}'. "
            "Start with simple observation and identity sentences, then move into small concrete actions. "
            f"Keep the tone warm, clear, and {level_details} friendly, while advancing the situation from the previous block."
        )
        for block_index in range(1, block_count + 1)
    ]

def build_narrative_generator_language_config(
    language_config: LanguageConfig,
) -> NarrativeGeneratorLanguageConfig:
    """Build narrative-step config from the broader LanguageConfig."""
    default_builder = fallback_default_blocks
    return NarrativeGeneratorLanguageConfig(
        canonical_language=language_config.canonical_language,
        default_block_builder=default_builder,
    )
