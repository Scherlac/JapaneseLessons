from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from jlesson.language_config import LanguageConfig


@dataclass(frozen=True)
class NarrativeGeneratorLanguageConfig:
    """Language-specific configuration used only by the narrative generator step."""

    source_language_label: str
    default_block_builder: Callable[[str, int, int], list[str]]



def _fallback_default_blocks(theme: str, lesson_number: int, block_count: int) -> list[str]:
    return [
        (
            f"Lesson {lesson_number}, block {index}, stays on the theme '{theme}'. "
            "Describe concrete beginner-level situations and move the story forward."
        )
        for index in range(1, block_count + 1)
    ]



def build_narrative_generator_language_config(
    language_config: LanguageConfig,
) -> NarrativeGeneratorLanguageConfig:
    """Build narrative-step config from the broader LanguageConfig."""
    default_builder = _fallback_default_blocks
    if language_config.generator is not None:
        default_builder = language_config.generator.build_default_narrative_blocks
    return NarrativeGeneratorLanguageConfig(
        source_language_label=language_config.source.display_name,
        default_block_builder=default_builder,
    )
