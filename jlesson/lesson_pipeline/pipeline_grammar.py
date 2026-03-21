from __future__ import annotations

from jlesson.models import GrammarItem


def coerce_grammar_items(
    grammar_items: list[GrammarItem | dict],
) -> list[GrammarItem]:
    coerced: list[GrammarItem] = []
    for item in grammar_items:
        if isinstance(item, GrammarItem):
            coerced.append(item)
        else:
            coerced.append(GrammarItem(**item))
    return coerced


def grammar_id(grammar: GrammarItem | dict) -> str:
    if isinstance(grammar, GrammarItem):
        return grammar.id
    return str(grammar.get("id", ""))