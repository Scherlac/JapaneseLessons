from __future__ import annotations


def build_vocab_gap_fill_prompt(
    theme: str,
    narrative_block: str,
    available_nouns: list[str],
    available_verbs: list[str],
    target_nouns: int,
    target_verbs: int,
) -> str:
    """Build a prompt asking the LLM to select the most narrative-relevant vocab items.

    Used when file-based matching cannot fill the requested quota from the
    narrative terms alone.  The LLM picks from the *available* pool rather
    than synthesising new items, keeping responses grounded and deterministic.

    Parameters
    ----------
    theme:
        The lesson theme (e.g. "kiki's delivery service").
    narrative_block:
        The story text for the current block.
    available_nouns:
        Source-language noun identifiers that have not yet been covered.
    available_verbs:
        Source-language verb identifiers that have not yet been covered.
    target_nouns:
        How many nouns the caller still needs.
    target_verbs:
        How many verbs the caller still needs.
    """
    noun_list = "\n".join(f"  - {n}" for n in available_nouns) or "  (none available)"
    verb_list = "\n".join(f"  - {v}" for v in available_verbs) or "  (none available)"

    return f"""\
You are a language-lesson curriculum designer.

THEME:
    {theme}

CURRENT NARRATIVE BLOCK:
    {narrative_block}

AVAILABLE NOUNS (not yet covered):
{noun_list}

AVAILABLE VERBS (not yet covered):
{verb_list}

TASK:
Select the {target_nouns} noun(s) and {target_verbs} verb(s) from the lists above that
best support a beginner learner practising in the context of the narrative block.
Choose items that appear naturally in the scene or would help describe it.
Only select from the provided lists — do not invent new words.

Return ONLY a raw JSON object with no prose:
{{
    "nouns": ["word1", "word2"],
    "verbs": ["word1", "word2"]
}}
""".strip()
