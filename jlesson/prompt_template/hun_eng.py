"""
Hungarian-English prompt builders.

All functions return plain-text or JSON-schema prompt strings for the hun-eng
language pair.  Consumed by HunEngPrompts (the PromptInterface adapter) and
directly by legacy call sites.

Target audience: Hungarian-speaking children (ages 8-12) learning English.
All instructions and memory tips are in Hungarian.
"""

from __future__ import annotations

from ..models import GeneralItem, GrammarItem, Sentence
from ._base import (
    PromptInterface,
    build_narrative_generator_prompt,
    build_narrative_vocab_extract_prompt,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

HUNGARIAN_PERSONS: list[tuple[str, str, str]] = [
    ("I",    "én",        "aɪ"),
    ("You",  "te",        "juː"),
    ("He",   "ő (fiú)",   "hiː"),
    ("She",  "ő (lány)",  "ʃiː"),
    ("We",   "mi",        "wiː"),
    ("They", "ők",        "ðeɪ"),
]

HUNGARIAN_GRAMMAR_PATTERNS: list[dict] = [
    {
        "name": "Subject + verb + object",
        "pattern": "S + V + O",
        "description": "Alapmondat — alany + ige + tárgy",
    },
    {
        "name": "Subject + is/am/are + noun/adjective",
        "pattern": "S + be + N/Adj",
        "description": "Létige — alany + létige + főnév/melléknév",
    },
    {
        "name": "There is/are + noun",
        "pattern": "There + be + N",
        "description": "Létezés — Van valami valahol",
    },
]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _format_hungarian_noun_list(nouns: list[GeneralItem]) -> str:
    lines = []
    for i, n in enumerate(nouns, 1):
        lines.append(
            f"  {i}. {n.target.display_text} — {n.source.display_text} "
            f"(pronunciation: {n.target.pronunciation})"
        )
    return "\n".join(lines)


def _format_hungarian_verb_list(verbs: list[GeneralItem]) -> str:
    lines = []
    for i, v in enumerate(verbs, 1):
        past = v.target.extra.get("past_tense", "?")
        lines.append(
            f"  {i}. {v.target.display_text} — {v.source.display_text} "
            f"(pronunciation: {v.target.pronunciation}) → past tense: {past}"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public builders
# ---------------------------------------------------------------------------

def hungarian_build_lesson_prompt(
    theme: str,
    nouns: list[dict],
    verbs: list[dict],
    persons: list[tuple[str, str, str]] | None = None,
    grammar_patterns: list[dict] | None = None,
    noun_reps: int = 5,
    verb_reps: int = 5,
    grammar_reps: int = 3,
) -> str:
    """Build a complete lesson prompt for Hungarian children learning English."""
    persons = persons or HUNGARIAN_PERSONS
    grammar_patterns = grammar_patterns or HUNGARIAN_GRAMMAR_PATTERNS

    noun_block = _format_hungarian_noun_list(nouns)
    verb_block = _format_hungarian_verb_list(verbs)
    person_block = "\n".join(
        f"  - {en}: {hu} (pronunciation: {pron})" for en, hu, pron in persons
    )
    pattern_block = "\n".join(
        f"  {i}. **{p['name']}**: {p['pattern']} — {p['description']}"
        for i, p in enumerate(grammar_patterns, 1)
    )
    noun_total = len(nouns) * noun_reps
    verb_total = len(verbs) * verb_reps
    grammar_sentences = len(grammar_patterns) * len(persons)
    grammar_total = grammar_sentences * grammar_reps

    return f"""\
You are an English teacher teaching English to Hungarian children aged 8-12.

=== LESSON THEME: {theme.upper()} ===

Generate a complete lesson following the exact structure below.
Use ONLY the provided vocabulary. Do NOT add extra words.
All explanations should be in Hungarian; target-language examples in English.

--- VOCABULARY ---

NOUNS ({len(nouns)} items):
{noun_block}

VERBS ({len(verbs)} items):
{verb_block}

--- LESSON STRUCTURE ---

## PART 1 — NOUNS

For EACH noun, produce {noun_reps} repetitions ({noun_total} total):

  1. [INTRODUCE]    Hungarian → English (with pronunciation)
  2. [RECALL]       English → Hungarian (learner recalls the meaning)
  3. [REINFORCE]    Hungarian → English (confirm again)
  4. [CHECK]        English sentence using the word
  5. [LOCK-IN]      Hungarian → English (final repetition)

## PART 2 — VERBS

Same repetition cycle for each verb ({verb_reps} repetitions, {verb_total} total).
For each verb, also show the past tense form.

## PART 3 — GRAMMAR

Persons:
{person_block}

Grammar patterns:
{pattern_block}

For each pattern, generate sentences using different persons.
Repetition cycle per sentence ({grammar_reps} repetitions):
  1. [TRANSLATE]    Hungarian → English
  2. [COMPREHEND]   English → Hungarian
  3. [REINFORCE]    Hungarian → English

Use only the vocabulary listed above in the sentences.

--- OUTPUT FORMAT ---

Use Markdown. Use clear headings for each part and sub-section.
Number every item so the learner can track progress.

Total repetitions: {noun_total} + {verb_total} + {grammar_total} = {noun_total + verb_total + grammar_total}

Begin the lesson now.
"""


def hungarian_build_vocab_prompt(
    theme: str,
    num_nouns: int = 12,
    num_verbs: int = 10,
    level: str = "beginner",
) -> str:
    """Build an LLM prompt that asks for a Hungarian-English vocabulary JSON file."""
    return f"""\
You are an English language teacher creating a vocabulary list for Hungarian children aged 8-12.

Generate a JSON vocabulary file for the theme: **{theme}**

Requirements:
- Exactly {num_nouns} nouns and {num_verbs} verbs.
- All words should be common, practical, {level}-appropriate, and suitable for children.
- Each noun must have: english, hungarian, pronunciation (English IPA).
- Each verb must have: english, hungarian, pronunciation, past_tense (the English past tense form).
- Output ONLY valid JSON, no commentary before or after.
- Use the exact schema below.

Schema example:
```json
{{
  "theme": "{theme}",
  "nouns": [
    {{"english": "dog", "hungarian": "kutya", "pronunciation": "ˈdɒɡ"}}
  ],
  "verbs": [
    {{"english": "to eat", "hungarian": "enni", "pronunciation": "ˈiːt", "past_tense": "ate"}}
  ]
}}
```

Now generate the complete JSON for theme "{theme}" with {num_nouns} nouns and {num_verbs} verbs.
""".strip()


def hungarian_build_narrative_vocab_generate_prompt(
    nouns: list[str],
    verbs: list[str],
    theme: str,
) -> str:
    """Build a prompt to generate Hungarian-English vocab entries for narrative terms."""
    noun_lines = "\n".join(f"  {i + 1}. {n}" for i, n in enumerate(nouns))
    verb_lines = "\n".join(f"  {i + 1}. {v}" for i, v in enumerate(verbs))
    total = len(nouns) + len(verbs)
    return f"""\
You are an English language expert building vocabulary for a Hungarian children's lesson about "{theme}".

Provide Hungarian translations and English pronunciations for the following English words.

NOUNS ({len(nouns)}):
{noun_lines}

VERBS ({len(verbs)}):
{verb_lines}

Rules:
- Output exactly {total} entries — one per word above, in the same order.
- Each noun entry must have: english, hungarian, pronunciation (English IPA).
- Each verb entry must have: english, hungarian, pronunciation (English IPA),
  past_tense (the irregular or regular English past tense form, e.g. "loved" or "went").
- Use beginner-appropriate vocabulary suitable for children aged 8-12.
- Output ONLY a raw JSON object in this exact schema:
{{
  "theme": "{theme}",
  "nouns": [
    {{"english": "...", "hungarian": "...", "pronunciation": "..."}}
  ],
  "verbs": [
    {{"english": "...", "hungarian": "...", "pronunciation": "...", "past_tense": "..."}}
  ]
}}
""".strip()


def hungarian_build_noun_practice_prompt(
    nouns: list[GeneralItem],
    lesson_number: int = 1,
) -> str:
    """Build a prompt for an LLM to generate focused noun introduction content."""
    noun_block = _format_hungarian_noun_list(nouns)
    return f"""\
You are an English teacher writing the noun introduction for lesson {lesson_number}, \
aimed at Hungarian children aged 8-12.

NOUNS TO INTRODUCE:
{noun_block}

For each noun, produce a JSON entry with:
- english, hungarian, pronunciation  (copy exactly from the list above)
- example_sentence_en  — a short, natural English sentence using the word
- example_sentence_hu  — the Hungarian translation of that sentence
- memory_tip           — a memory aid written in Hungarian that helps remember \
the English word (e.g. a similar-sounding Hungarian word, a visual image, a funny sentence)

The memory_tip should be creative and child-friendly — use Hungarian words or \
concepts that an 8-12 year old would know.

Return ONLY a raw JSON object — no markdown fences, no commentary:
{{
  "noun_items": [
    {{
      "english": "...",
      "hungarian": "...",
      "pronunciation": "...",
      "example_sentence_en": "...",
      "example_sentence_hu": "...",
      "memory_tip": "..."
    }}
  ]
}}
""".strip()


def hungarian_build_verb_practice_prompt(
    verbs: list[GeneralItem],
    lesson_number: int = 1,
) -> str:
    """Build a prompt for an LLM to generate focused verb introduction content."""
    verb_block = _format_hungarian_verb_list(verbs)
    return f"""\
You are an English teacher writing the verb introduction for lesson {lesson_number}, \
aimed at Hungarian children aged 8-12.

VERBS TO INTRODUCE:
{verb_block}

For each verb, produce a JSON entry with:
- english, hungarian, pronunciation, past_tense  (copy exactly from the list above)
- example_sentence_en  — a short, natural English sentence using the verb (present tense)
- example_sentence_hu  — the Hungarian translation of that sentence
- memory_tip           — a memory aid written in Hungarian that helps remember \
the English verb and its past tense form

The memory_tip should briefly explain:
- For regular verbs (e.g. walk → walked): "Just add -ed!"
- For irregular verbs (e.g. eat → ate): give a fun tip about the irregular form

Tips must be in Hungarian and child-friendly — use words and analogies \
that an 8-12 year old Hungarian child would understand.

Return ONLY a raw JSON object — no markdown fences, no commentary:
{{
  "verb_items": [
    {{
      "english": "...",
      "hungarian": "...",
      "pronunciation": "...",
      "past_tense": "...",
      "example_sentence_en": "...",
      "example_sentence_hu": "...",
      "memory_tip": "..."
    }}
  ]
}}
""".strip()


def hungarian_build_grammar_select_prompt(
    unlocked_grammar: list[GrammarItem],
    available_nouns: list[GeneralItem],
    available_verbs: list[GeneralItem],
    lesson_number: int,
    covered_grammar_ids: list[str],
    selection_count: int = 2,
) -> str:
    """Ask the LLM which Hungarian→English grammar point to teach next."""
    grammar_lines = "\n".join(
        f"  - id: {g.id}\n"
        f"    pattern: {g.pattern}\n"
        f"    description: {g.description}\n"
        f"    example: {g.example_source} → {g.example_target}\n"
        f"    level: {g.level}"
        for g in unlocked_grammar
    )
    noun_names = ", ".join(n.source.display_text for n in available_nouns)
    verb_names = ", ".join(v.source.display_text for v in available_verbs)
    covered_str = ", ".join(covered_grammar_ids) if covered_grammar_ids else "(none)"

    return f"""\
You are an English curriculum designer planning lesson {lesson_number} \
for Hungarian children aged 8-12.

ALREADY COVERED GRAMMAR:
  {covered_str}

AVAILABLE VOCABULARY FOR THIS LESSON:
  Nouns: {noun_names}
  Verbs: {verb_names}

UNLOCKED GRAMMAR STEPS (prerequisites met, not yet taught):
{grammar_lines}

TASK:
Select between 1 and {selection_count} grammar IDs from the unlocked list that are:
1. Appropriate difficulty for lesson {lesson_number} (prefer lower level first)
2. Compatible with the available vocabulary (can form natural practice sentences)
3. If this is an early lesson, prefer level-1 steps before level-2

Return ONLY a raw JSON object — no markdown fences, no commentary:
{{
  "selected_ids": ["<id1>"],
  "rationale": "One sentence explaining why these grammar points were chosen."
}}
""".strip()


def hungarian_build_grammar_generate_prompt(
    grammar_specs: list[GrammarItem],
    nouns: list[GeneralItem],
    verbs: list[GeneralItem],
    persons: list[tuple[str, str, str]] | None = None,
    sentences_per_grammar: int = 3,
    narrative: str = "",
) -> str:
    """Generate English practice sentences with Hungarian translations."""
    persons = persons or HUNGARIAN_PERSONS

    grammar_block = "\n".join(
        f"  [{g.id}] {g.pattern} — {g.description}\n"
        f"  Example: {g.example_source} → {g.example_target}"
        for g in grammar_specs
    )
    noun_block = _format_hungarian_noun_list(nouns)
    verb_block = _format_hungarian_verb_list(verbs)
    person_lines = "\n".join(
        f"  - {en}: {hu} (pronunciation: {pron})" for en, hu, pron in persons
    )
    total = len(grammar_specs) * sentences_per_grammar
    narrative_block = (
        f"\nNARRATIVE CONTEXT:\n{narrative.strip()}\n"
        if narrative and narrative.strip()
        else ""
    )

    return f"""\
You are an English teacher writing practice sentences for Hungarian children aged 8-12.

GRAMMAR POINTS TO PRACTICE:
{grammar_block}

VOCABULARY TO USE (use only these words):
Nouns:
{noun_block}

Verbs:
{verb_block}

PERSONS:
{person_lines}
{narrative_block}

TASK:
For each grammar point, generate {sentences_per_grammar} natural English sentences \
using the vocabulary above. Cover different persons across the sentences.
Total: {total} sentences.
If narrative context is provided, keep the sentence set consistent with that story arc.

Each sentence must include:
- grammar_id  — which grammar point this sentence practises
- english     — natural English sentence
- hungarian   — correct Hungarian translation
- person      — which person (I / You / He / She / We / They)
- notes       — brief grammar note in English (e.g. which tense, which word order)

Return ONLY a raw JSON object — no markdown fences, no commentary:
{{
  "sentences": [
    {{
      "grammar_id": "...",
      "english": "...",
      "hungarian": "...",
      "person": "...",
      "notes": "..."
    }}
  ]
}}
""".strip()


def hungarian_build_sentence_review_prompt(
    sentences: list[Sentence],
    nouns: list[GeneralItem],
    verbs: list[GeneralItem],
    grammar_specs: list[GrammarItem],
) -> str:
    """Review English sentences for correctness and age-appropriateness."""
    sentence_lines = "\n".join(
        f"  [{i}] grammar: {s.grammar_id}\n"
        f"       EN: {s.source.display_text}\n"
        f"       HU: {s.target.display_text}\n"
        f"       Person: {s.grammar_parameters.get('person', '')}"
        for i, s in enumerate(sentences)
    )
    grammar_block = "\n".join(
        f"  [{g.id}] {g.pattern} — {g.description}"
        for g in grammar_specs
    )
    noun_names = ", ".join(
        f"{n.target.display_text} ({n.source.display_text})" for n in nouns
    )
    verb_names = ", ".join(
        f"{v.target.display_text} ({v.source.display_text})" for v in verbs
    )

    return f"""\
You are a native English language expert reviewing practice sentences \
created for Hungarian children aged 8-12.

These sentences were generated by combining vocabulary and grammar patterns independently.
Some combinations may be forced or unnatural. \
Your job is to identify and fix such sentences.

GRAMMAR PATTERNS USED:
{grammar_block}

AVAILABLE VOCABULARY:
  Nouns: {noun_names}
  Verbs: {verb_names}

SENTENCES TO REVIEW:
{sentence_lines}

TASK:
Rate each sentence on a 1-5 scale for naturalness and child-friendliness:
  5 = Perfectly natural — a native speaker would say this
  4 = Natural enough — slightly textbook-ish but acceptable
  3 = Borderline — grammatically correct but feels forced
  2 = Unnatural — awkward word or grammar combination
  1 = Nonsensical — the words do not fit this grammar pattern

IMPORTANT: sentences must be understandable to children aged 8-12!

For any sentence scoring BELOW 3, provide a revised version that:
- Uses the SAME grammar pattern (grammar_id stays the same)
- Uses vocabulary from the available pool above (may swap nouns/verbs for better fit)
- Keeps the same person where possible
- Is natural and child-friendly
- Uses correct English grammar

If a sentence scores 3 or above, set "revised_sentence" to null.

Return ONLY a raw JSON object — no markdown fences, no commentary:
{{
  "reviews": [
    {{
      "index": 0,
      "score": 4,
      "is_natural": true,
      "issue": null,
      "revised_sentence": null
    }},
    {{
      "index": 1,
      "score": 2,
      "is_natural": false,
      "issue": "Existence pattern does not pair naturally with the action verb 'to eat'",
      "revised_sentence": {{
        "grammar_id": "...",
        "english": "...",
        "hungarian": "...",
        "person": "...",
        "notes": "..."
      }}
    }}
  ],
  "overall_naturalness": <1-5 average>
}}
""".strip()


# ---------------------------------------------------------------------------
# PromptInterface adapter
# ---------------------------------------------------------------------------

class HunEngPrompts(PromptInterface):
    """Prompt builders for Hungarian-English lessons."""

    def build_grammar_select_prompt(
        self,
        unlocked_grammar: list[GrammarItem],
        available_nouns: list[GeneralItem],
        available_verbs: list[GeneralItem],
        lesson_number: int,
        covered_grammar_ids: list[str],
        selection_count: int = 2,
    ) -> str:
        return hungarian_build_grammar_select_prompt(
            unlocked_grammar, available_nouns, available_verbs,
            lesson_number, covered_grammar_ids, selection_count,
        )

    def build_narrative_generator_prompt(
        self,
        theme: str,
        lesson_number: int,
        lesson_blocks: int,
        seed_blocks: list[str] | None = None,
    ) -> str:
        return build_narrative_generator_prompt(
            theme, lesson_number, lesson_blocks,
            source_language_label="Hungarian",
            seed_blocks=seed_blocks,
        )

    def build_narrative_vocab_extract_prompt(
        self,
        narrative_blocks: list[str],
        nouns_per_block: int,
        verbs_per_block: int,
    ) -> str:
        return build_narrative_vocab_extract_prompt(
            narrative_blocks,
            source_language_label="Hungarian",
            nouns_per_block=nouns_per_block,
            verbs_per_block=verbs_per_block,
        )

    def build_narrative_vocab_generate_prompt(
        self,
        nouns: list[str],
        verbs: list[str],
        theme: str,
    ) -> str:
        return hungarian_build_narrative_vocab_generate_prompt(nouns, verbs, theme)

    def build_grammar_generate_prompt(
        self,
        grammar_specs: list[GrammarItem],
        nouns: list[GeneralItem],
        verbs: list[GeneralItem],
        persons: list[tuple[str, str, str]] | None = None,
        sentences_per_grammar: int = 3,
        narrative: str = "",
    ) -> str:
        return hungarian_build_grammar_generate_prompt(
            grammar_specs, nouns, verbs, persons, sentences_per_grammar, narrative,
        )

    def build_sentence_review_prompt(
        self,
        sentences: list[Sentence],
        nouns: list[GeneralItem],
        verbs: list[GeneralItem],
        grammar_specs: list[GrammarItem],
    ) -> str:
        return hungarian_build_sentence_review_prompt(sentences, nouns, verbs, grammar_specs)

    def build_noun_practice_prompt(
        self,
        noun_items: list[GeneralItem],
        lesson_number: int,
    ) -> str:
        return hungarian_build_noun_practice_prompt(noun_items, lesson_number)

    def build_verb_practice_prompt(
        self,
        verb_items: list[GeneralItem],
        lesson_number: int,
    ) -> str:
        return hungarian_build_verb_practice_prompt(verb_items, lesson_number)
