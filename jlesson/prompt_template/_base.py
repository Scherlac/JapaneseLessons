"""
Shared prompt builders and abstract interface used by all language pairs.

language-agnostic builders
    build_narrative_generator_prompt   — block narrative (takes source_language_label)
    build_narrative_vocab_extract_prompt — vocab extraction (takes source_language_label)

Abstract base class
    PromptInterface — contract that every language-pair adapter must satisfy.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import GeneralItem, GrammarItem, Sentence


# ---------------------------------------------------------------------------
# Shared (language-agnostic) builders
# ---------------------------------------------------------------------------

def build_narrative_generator_prompt(
    theme: str,
    lesson_number: int,
    lesson_blocks: int,
    source_language_label: str,
    seed_blocks: list[str] | None = None,
) -> str:
    seed_lines = "\n".join(
        f"  - Block {index}: {text}"
        for index, text in enumerate(seed_blocks or [], 1)
        if text.strip()
    ) or "  (none)"

    return f"""\
You are a curriculum writer planning a beginner-friendly lesson narrative.

THEME:
    {theme}

LESSON NUMBER:
    {lesson_number}

TARGET BLOCK COUNT:
    {lesson_blocks}

WRITE THE BLOCK NARRATIVE IN:
    {source_language_label}

OPTIONAL USER-PROVIDED SEED BLOCKS:
{seed_lines}

TASK:
Create a narrative progression with {lesson_blocks} blocks.
Each block should be 2-4 short sentences of story context.
Keep the overall situation coherent, but make each block meaningfully different.
The progression should stay concrete and beginner-friendly.

Return ONLY a raw JSON object:
{{
    "blocks": [
        {{"index": 1, "narrative": "..."}}
    ]
}}
""".strip()


def build_narrative_vocab_extract_prompt(
    narrative_blocks: list[str],
    source_language_label: str,
    nouns_per_block: int,
    verbs_per_block: int,
) -> str:
    block_lines = "\n".join(
        f"  [{index}] {text}"
        for index, text in enumerate(narrative_blocks, 1)
    )

    return f"""\
You are extracting teachable vocabulary from story blocks.

SOURCE LANGUAGE OF THE STORY:
    {source_language_label}

BLOCKS:
{block_lines}

TASK:
For each block, extract up to {nouns_per_block} concrete noun phrases and up to {verbs_per_block} verb phrases.
Return the terms in their plain dictionary form in the source language.
Prefer words that are central to the block and teachable for beginners.

Return ONLY a raw JSON object:
{{
    "blocks": [
        {{
            "index": 1,
            "nouns": ["..."],
            "verbs": ["..."]
        }}
    ]
}}
""".strip()


# ---------------------------------------------------------------------------
# Abstract interface
# ---------------------------------------------------------------------------

class PromptInterface(ABC):
    """Abstract interface for language-specific prompt builders."""

    @abstractmethod
    def build_grammar_select_prompt(
        self,
        unlocked_grammar: list[GrammarItem],
        available_nouns: list[GeneralItem],
        available_verbs: list[GeneralItem],
        lesson_number: int,
        covered_grammar_ids: list[str],
        selection_count: int = 2,
    ) -> str:
        """Build prompt for selecting grammar points."""
        ...

    @abstractmethod
    def build_narrative_generator_prompt(
        self,
        theme: str,
        lesson_number: int,
        lesson_blocks: int,
        seed_blocks: list[str] | None = None,
    ) -> str:
        """Build prompt for generating a block-by-block narrative progression."""
        ...

    @abstractmethod
    def build_narrative_vocab_extract_prompt(
        self,
        narrative_blocks: list[str],
        nouns_per_block: int,
        verbs_per_block: int,
    ) -> str:
        """Build prompt for extracting key vocabulary targets from narrative blocks."""
        ...

    @abstractmethod
    def build_narrative_vocab_generate_prompt(
        self,
        nouns: list[str],
        verbs: list[str],
        theme: str,
    ) -> str:
        """Build prompt to generate full target-language vocab entries for narrative terms."""
        ...

    @abstractmethod
    def build_grammar_generate_prompt(
        self,
        grammar_specs: list[GrammarItem],
        nouns: list[GeneralItem],
        verbs: list[GeneralItem],
        persons: list[tuple[str, str, str]] | None = None,
        sentences_per_grammar: int = 3,
        narrative: str = "",
    ) -> str:
        """Build prompt for generating grammar sentences."""
        ...

    @abstractmethod
    def build_sentence_review_prompt(
        self,
        sentences: list[Sentence],
        nouns: list[GeneralItem],
        verbs: list[GeneralItem],
        grammar_specs: list[GrammarItem],
    ) -> str:
        """Build prompt for reviewing sentences."""
        ...

    @abstractmethod
    def build_noun_practice_prompt(
        self,
        noun_items: list[GeneralItem],
        lesson_number: int,
    ) -> str:
        """Build prompt for noun practice."""
        ...

    @abstractmethod
    def build_verb_practice_prompt(
        self,
        verb_items: list[GeneralItem],
        lesson_number: int,
    ) -> str:
        """Build prompt for verb practice."""
        ...
