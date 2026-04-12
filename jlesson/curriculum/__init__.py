"""
curriculum — public facade.

This package replaces the old monolithic ``curriculum.py``.
All public names are re-exported here so that existing import statements
continue to work unchanged:

    from jlesson.curriculum import create_curriculum, GRAMMAR_PROGRESSION, ...
"""

# Language-agnostic CRUD and grammar helpers
from ._base import (
    CurriculumData,
    LessonRecord,
    create_curriculum,
    load_curriculum,
    save_curriculum,
    add_lesson,
    replace_lesson,
    complete_lesson,
    recompute_coverage,
    get_next_grammar_from,
    grammar_summary_lines,
)

# Japanese
from .jap import (
    JAP_GRAMMAR_PROGRESSION,
    GRAMMAR_PROGRESSION,       # backward compat
    ENG_TO_JAP_GRAMMAR_PROGRESSION,  # backward compat
    get_next_grammar,
    get_grammar_by_id,
    summary,
)

# French
from .fre import (
    FRE_GRAMMAR_PROGRESSION,
    ENG_TO_FRE_GRAMMAR_PROGRESSION,  # backward compat
)

# English (as target)
from .eng import (
    ENG_GRAMMAR_PROGRESSION,
    HUN_TO_ENG_GRAMMAR_PROGRESSION,  # backward compat
)

# German (as target)
from .ger import (
    GER_GRAMMAR_PROGRESSION,
    HUN_TO_GER_GRAMMAR_PROGRESSION,  # backward compat
)

__all__ = [
    # base
    "create_curriculum",
    "load_curriculum",
    "save_curriculum",
    "add_lesson",
    "replace_lesson",
    "complete_lesson",
    "recompute_coverage",
    "get_next_grammar_from",
    "grammar_summary_lines",
    # Japanese
    "JAP_GRAMMAR_PROGRESSION",
    "GRAMMAR_PROGRESSION",
    "ENG_TO_JAP_GRAMMAR_PROGRESSION",
    "get_next_grammar",
    "get_grammar_by_id",
    "summary",
    # French
    "FRE_GRAMMAR_PROGRESSION",
    "ENG_TO_FRE_GRAMMAR_PROGRESSION",
    # English (as target)
    "ENG_GRAMMAR_PROGRESSION",
    "HUN_TO_ENG_GRAMMAR_PROGRESSION",
    # German (as target)
    "GER_GRAMMAR_PROGRESSION",
    "HUN_TO_GER_GRAMMAR_PROGRESSION",
]
