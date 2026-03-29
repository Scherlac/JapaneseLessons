"""Language-agnostic prompt helpers for the narrative_grammar step."""
from __future__ import annotations

from jlesson.models import GeneralItem, GrammarItem

# Extra target-side keys shown verbatim inside the vocab block.
# Any language pair may produce these fields on GeneralItem.target.extra.
_NOTABLE_EXTRA_KEYS: tuple[str, ...] = ("kanji", "masu_form", "type", "past_tense")


def format_vocab_items(items: list[GeneralItem]) -> str:
    """Format a list of GeneralItem objects for inclusion in an LLM prompt.

    Uses only generic ``GeneralItem`` fields (``source``, ``target``,
    ``pronunciation``, ``extra``) so this helper is language-pair agnostic.
    Notable extra keys (kanji, masu_form, type, past_tense) are appended in
    brackets when present.
    """
    lines = []
    for index, item in enumerate(items, 1):
        src = item.source.display_text
        tgt = item.target.display_text
        phonetic = item.target.pronunciation
        extras = [
            f"{key}: {val}"
            for key in _NOTABLE_EXTRA_KEYS
            if (val := item.target.extra.get(key))
        ]
        row = f"  {index}. {src} → {tgt}"
        if phonetic:
            row += f" ({phonetic})"
        if extras:
            row += f" [{', '.join(extras)}]"
        lines.append(row)
    return "\n".join(lines)


def build_grammar_sentences_prompt(
    grammar_specs: list[GrammarItem],
    nouns: list[GeneralItem],
    verbs: list[GeneralItem],
    *,
    persons: list[tuple[str, str, str]],
    sentences_per_grammar: int = 3,
    narrative: str = "",
    teacher_description: str = "a language teacher",
    output_source_field: str = "source_text",
    output_target_field: str = "target_text",
    output_phonetic_field: str = "",
) -> str:
    """Build a language-agnostic grammar sentence generation prompt.

    Vocabulary is formatted via :func:`format_vocab_items` which uses generic
    ``GeneralItem`` fields, making this builder reusable across language pairs.

    Output JSON field names are caller-supplied and **must match the keys that**
    **``ItemGenerator.convert_sentence`` reads**, so LLM responses remain
    compatible with the existing language-specific converters without changes.

    Parameters
    ----------
    grammar_specs:
        Grammar points to practise in this block.
    nouns / verbs:
        Lesson vocabulary for this block (fully converted ``GeneralItem`` objects).
    persons:
        Tuples of (native_label, target_label, phonetic) from the step config.
    sentences_per_grammar:
        How many sentences to generate per grammar point.
    narrative:
        Optional story passage; when given the LLM keeps sentences contextually
        consistent with the scene.
    teacher_description:
        LLM system framing, e.g. ``"a Japanese language teacher"``.
    output_source_field / output_target_field / output_phonetic_field:
        JSON key names for the response schema (language-pair specific).
        ``output_phonetic_field`` may be empty — the field is then omitted.
    """
    grammar_block = "\n".join(
        f"  [{g.id}] {g.pattern} — {g.description}\n"
        f"  Example: {g.example_source} → {g.example_target}"
        for g in grammar_specs
    )
    noun_block = format_vocab_items(nouns)
    verb_block = format_vocab_items(verbs)
    person_lines = "\n".join(
        f"  - {native} ({target})" + (f" [{phonetic}]" if phonetic else "")
        for native, target, phonetic in persons
    )
    total = len(grammar_specs) * sentences_per_grammar
    narrative_section = (
        f"\nNARRATIVE CONTEXT:\n{narrative.strip()}\n"
        if narrative and narrative.strip()
        else ""
    )

    # Build JSON schema fields dynamically so the schema is always self-consistent.
    schema_fields = [
        f'      "grammar_id": "..."',
        f'      "{output_source_field}": "..."',
        f'      "{output_target_field}": "..."',
    ]
    if output_phonetic_field:
        schema_fields.append(f'      "{output_phonetic_field}": "..."')
    schema_fields += ['      "person": "..."', '      "notes": "..."']
    schema_inner = ",\n".join(schema_fields)

    phonetic_doc = (
        f"\n- {output_phonetic_field:<24} — phonetic annotation"
        if output_phonetic_field
        else ""
    )

    return f"""\
You are {teacher_description} generating grammar practice sentences.

GRAMMAR POINTS TO PRACTISE:
{grammar_block}

VOCABULARY (use only these items):
Nouns:
{noun_block}

Verbs:
{verb_block}

PERSONS:
{person_lines}
{narrative_section}
TASK:
For each grammar point, generate {sentences_per_grammar} natural sentences using the
vocabulary above. Cover different persons across sentences. Total: {total} sentences.
If narrative context is provided, keep sentences consistent with that story arc.

Each sentence must include:
- grammar_id               — which grammar point this sentence demonstrates
- {output_source_field:<24} — source-language sentence
- {output_target_field:<24} — target-language sentence{phonetic_doc}
- person                   — which person (from the PERSONS list)
- notes                    — brief grammar note (particle, conjugation, etc.)

Return ONLY a raw JSON object — no markdown fences, no commentary:
{{
  "sentences": [
    {{
{schema_inner}
    }}
  ]
}}""".strip()
