from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from jlesson.language_config import LanguageConfig


@dataclass(frozen=True)
class NarrativeGeneratorLanguageConfig:
    """Language-specific configuration used only by the narrative generator step."""

    source_language_label: str
    default_block_builder: Callable[[str, int, int], list[str]]


# ---------------------------------------------------------------------------
# Language-specific default block text (no ItemGenerator dependency)
# ---------------------------------------------------------------------------

def _eng_jap_default_blocks(theme: str, lesson_number: int, block_count: int) -> list[str]:
    return [
        (
            f"Lesson {lesson_number}, block {block_index}, stays in the world of '{theme}'. "
            "Start with simple observation and identity sentences, then move into small concrete actions. "
            "Keep the tone warm, clear, and beginner friendly, while advancing the situation from the previous block."
        )
        for block_index in range(1, block_count + 1)
    ]


def _hun_eng_default_blocks(theme: str, lesson_number: int, block_count: int) -> list[str]:
    return [
        (
            f"Lesson {lesson_number}, block {block_index}, uses the theme '{theme}'. "
            "Start with who the character is and where they are, then describe simple daily actions in that setting. "
            "Keep it suitable for beginner learners and let each block move the mini-story forward."
        )
        for block_index in range(1, block_count + 1)
    ]


def _fallback_default_blocks(theme: str, lesson_number: int, block_count: int) -> list[str]:
    return [
        (
            f"Lesson {lesson_number}, block {index}, stays on the theme '{theme}'. "
            "Describe concrete beginner-level situations and move the story forward."
        )
        for index in range(1, block_count + 1)
    ]


_DEFAULT_BLOCK_BUILDERS: dict[str, Callable[[str, int, int], list[str]]] = {
    "eng-jap": _eng_jap_default_blocks,
    "hun-eng": _hun_eng_default_blocks,
}


def build_narrative_generator_language_config(
    language_config: LanguageConfig,
) -> NarrativeGeneratorLanguageConfig:
    """Build narrative-step config from the broader LanguageConfig."""
    default_builder = _DEFAULT_BLOCK_BUILDERS.get(
        language_config.code, _fallback_default_blocks
    )
    return NarrativeGeneratorLanguageConfig(
        source_language_label=language_config.source.display_name,
        default_block_builder=default_builder,
    )
