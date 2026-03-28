"""
prompt_template — public facade.

This package replaces the old monolithic ``prompt_template.py``.
All public names are re-exported here so that existing import statements
continue to work unchanged:

    from .prompt_template import build_lesson_prompt, EngJapPrompts, ...
"""

# Shared / language-agnostic
from ._base import (
    PromptInterface,
    build_narrative_generator_prompt,
    build_narrative_vocab_extract_prompt,
)

# English-Japanese
from .eng_jap import (
    PERSONS_BEGINNER,
    GRAMMAR_PATTERNS_BEGINNER,
    DIMENSIONS_BEGINNER,
    EngJapPrompts,
    build_lesson_prompt,
    build_vocab_prompt,
    build_noun_practice_prompt,
    build_verb_practice_prompt,
    build_grammar_select_prompt,
    build_grammar_generate_prompt,
    build_content_validate_prompt,
    build_sentence_review_prompt,
    build_narrative_vocab_generate_prompt,
)

# Hungarian-English
from .hun_eng import (
    HUNGARIAN_PERSONS,
    HUNGARIAN_GRAMMAR_PATTERNS,
    HunEngPrompts,
    hungarian_build_lesson_prompt,
    hungarian_build_vocab_prompt,
    hungarian_build_narrative_vocab_generate_prompt,
    hungarian_build_noun_practice_prompt,
    hungarian_build_verb_practice_prompt,
    hungarian_build_grammar_select_prompt,
    hungarian_build_grammar_generate_prompt,
    hungarian_build_sentence_review_prompt,
)

__all__ = [
    # base
    "PromptInterface",
    "build_narrative_generator_prompt",
    "build_narrative_vocab_extract_prompt",
    # eng-jap
    "PERSONS_BEGINNER",
    "GRAMMAR_PATTERNS_BEGINNER",
    "DIMENSIONS_BEGINNER",
    "EngJapPrompts",
    "build_lesson_prompt",
    "build_vocab_prompt",
    "build_noun_practice_prompt",
    "build_verb_practice_prompt",
    "build_grammar_select_prompt",
    "build_grammar_generate_prompt",
    "build_content_validate_prompt",
    "build_sentence_review_prompt",
    "build_narrative_vocab_generate_prompt",
    # hun-eng
    "HUNGARIAN_PERSONS",
    "HUNGARIAN_GRAMMAR_PATTERNS",
    "HunEngPrompts",
    "hungarian_build_lesson_prompt",
    "hungarian_build_vocab_prompt",
    "hungarian_build_narrative_vocab_generate_prompt",
    "hungarian_build_noun_practice_prompt",
    "hungarian_build_verb_practice_prompt",
    "hungarian_build_grammar_select_prompt",
    "hungarian_build_grammar_generate_prompt",
    "hungarian_build_sentence_review_prompt",
]
