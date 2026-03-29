from __future__ import annotations

from jlesson.models import GrammarItem


def grammar_id(grammar: GrammarItem) -> str:
    return grammar.id
