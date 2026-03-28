"""
curriculum — public facade.

This package replaces the old monolithic ``curriculum.py``.
All public names are re-exported here so that existing import statements
continue to work unchanged:

    from jlesson.curriculum import create_curriculum, GRAMMAR_PROGRESSION, ...
"""

# Language-agnostic CRUD, vocab selection, and grammar helpers
from ._base import (
    create_curriculum,
    load_curriculum,
    save_curriculum,
    add_lesson,
    complete_lesson,
    get_next_grammar_from,
    grammar_summary_lines,
    suggest_new_vocab,
)

# English-Japanese
from .eng_jap import (
    ENG_TO_JAP_GRAMMAR_PROGRESSION,
    GRAMMAR_PROGRESSION,
    get_next_grammar,
    get_grammar_by_id,
    summary,
)

# Hungarian-English
from .hun_eng import HUN_TO_ENG_GRAMMAR_PROGRESSION

__all__ = [
    # base
    "create_curriculum",
    "load_curriculum",
    "save_curriculum",
    "add_lesson",
    "complete_lesson",
    "get_next_grammar_from",
    "grammar_summary_lines",
    "suggest_new_vocab",
    # eng-jap
    "ENG_TO_JAP_GRAMMAR_PROGRESSION",
    "GRAMMAR_PROGRESSION",
    "get_next_grammar",
    "get_grammar_by_id",
    "summary",
    # hun-eng
    "HUN_TO_ENG_GRAMMAR_PROGRESSION",
]
