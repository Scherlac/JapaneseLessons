"""
English → French prompt builders.

All functions return plain-text or JSON-schema prompt strings for the eng-fre
language pair.  Consumed by EngFrPrompts (the PromptInterface adapter) and
directly by call sites.

Target audience: English-speaking adults and teens beginning French.
Lesson instructions are in English; target-language content is in French.
"""

from __future__ import annotations

from ..models import GeneralItem, GrammarItem, Sentence
from ._base import (
    PromptInterface,
    build_narrative_vocab_extract_prompt,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FRENCH_PERSONS: list[tuple[str, str, str]] = [
    ("I",    "je",   "ʒə"),
    ("You",  "tu",   "ty"),
    ("He",   "il",   "il"),
    ("She",  "elle", "ɛl"),
    ("We",   "nous", "nu"),
    ("They", "ils/elles", "il/ɛl"),
]

FRENCH_GRAMMAR_PATTERNS: list[dict] = [
    {
        "name": "Sujet + verbe + objet",
        "pattern": "S + V + O",
        "description": "Basic declarative sentence",
    },
    {
        "name": "Sujet + être + nom/adjectif",
        "pattern": "S + être + N/Adj",
        "description": "Identity and description with être",
    },
    {
        "name": "Il y a + nom",
        "pattern": "Il y a + N",
        "description": "Existence — There is/are",
    },
]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _format_french_noun_list(nouns: list[GeneralItem]) -> str:
    lines = []
    for i, n in enumerate(nouns, 1):
        article = n.target.extra.get("article", "")
        article_prefix = f"{article} " if article else ""
        lines.append(
            f"  {i}. {article_prefix}{n.target.display_text} — {n.source.display_text} "
            f"(pronunciation: {n.target.pronunciation})"
        )
    return "\n".join(lines)


def _format_french_verb_list(verbs: list[GeneralItem]) -> str:
    lines = []
    for i, v in enumerate(verbs, 1):
        past_p = v.target.extra.get("past_participle", "?")
        auxiliary = v.target.extra.get("auxiliary", "avoir")
        lines.append(
            f"  {i}. {v.target.display_text} — {v.source.display_text} "
            f"(pronunciation: {v.target.pronunciation}) "
            f"→ passé composé: {auxiliary} + {past_p}"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public builders
# ---------------------------------------------------------------------------

def french_build_lesson_prompt(
    theme: str,
    nouns: list[dict],
    verbs: list[dict],
    persons: list[tuple[str, str, str]] | None = None,
    grammar_patterns: list[dict] | None = None,
    noun_reps: int = 5,
    verb_reps: int = 5,
    grammar_reps: int = 3,
) -> str:
    """Build a complete lesson prompt for English speakers learning French."""
    persons = persons or FRENCH_PERSONS
    grammar_patterns = grammar_patterns or FRENCH_GRAMMAR_PATTERNS

    noun_block = "\n".join(
        f"  {i}. {n.get('french', '')} — {n.get('english', '')} "
        f"(pronunciation: {n.get('pronunciation', '')}, article: {n.get('article', '')})"
        for i, n in enumerate(nouns, 1)
    ) if nouns and isinstance(nouns[0], dict) else _format_french_noun_list(nouns)  # type: ignore[arg-type]
    verb_block = "\n".join(
        f"  {i}. {v.get('french', '')} — {v.get('english', '')} "
        f"(pronunciation: {v.get('pronunciation', '')}, passé composé: {v.get('auxiliary', 'avoir')} + {v.get('past_participle', '?')})"
        for i, v in enumerate(verbs, 1)
    ) if verbs and isinstance(verbs[0], dict) else _format_french_verb_list(verbs)  # type: ignore[arg-type]
    person_block = "\n".join(
        f"  - {en}: {fr} (IPA: {ipa})" for en, fr, ipa in persons
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
You are a French teacher teaching French to English-speaking learners.

=== LESSON THEME: {theme.upper()} ===

Generate a complete lesson following the exact structure below.
Use ONLY the provided vocabulary. Do NOT add extra words.
All explanations should be in English; target-language examples in French.

--- VOCABULARY ---

NOUNS ({len(nouns)} words):
{noun_block}

VERBS ({len(verbs)} words):
{verb_block}

--- LESSON STRUCTURE ---

## PART 1 — NOUNS

For EACH noun generate {noun_reps} repetitions ({noun_total} total):
  1. [INTRODUCE]  English → French (with pronunciation and article)
  2. [RECALL]     French → English (learner recalls the meaning)
  3. [REINFORCE]  English → French (confirm again)
  4. [CHECK]      French sentence using the word
  5. [ANCHOR]     English → French (final repetition)

## PART 2 — VERBS

Same repetition cycle for each verb ({verb_reps} repetitions, {verb_total} total).
For each verb also show the passé composé form.

## PART 3 — GRAMMAR

Persons:
{person_block}

Grammar patterns:
{pattern_block}

For each pattern generate sentences across different persons.
Repetition cycle per sentence ({grammar_reps} repetitions):
  1. [TRANSLATE]   English → French
  2. [UNDERSTAND]  French → English
  3. [REINFORCE]   English → French

Use only the vocabulary listed above in the sentences.

--- OUTPUT FORMAT ---

Use Markdown. Use clear headings for each part and section.
Number each entry so the learner can track progress.

Total repetitions: {noun_total} + {verb_total} + {grammar_total} = {noun_total + verb_total + grammar_total}

Begin the lesson now.
"""


def french_build_vocab_prompt(
    theme: str,
    num_nouns: int = 12,
    num_verbs: int = 10,
    num_adjectives: int = 0,
    level: str = "beginner",
) -> str:
    """Build an LLM prompt that asks for an English-French vocabulary JSON file."""
    adj_requirement = (
        f"- Exactly {num_adjectives} adjectives.\n"
        "- Each adjective must have: french, english, pronunciation (French IPA).\n"
        if num_adjectives > 0 else ""
    )
    count_line = f"{num_nouns} nouns and {num_verbs} verbs"
    if num_adjectives > 0:
        count_line += f" and {num_adjectives} adjectives"
    adj_schema = (
        ',\n  "adjectives": [\n    {"french": "grand", "english": "big", "pronunciation": "ɡʁɑ̃"}\n  ]'
        if num_adjectives > 0 else ""
    )
    return f"""\
You are a French language teacher creating a vocabulary list for English-speaking learners.

Generate a JSON vocabulary file for the theme: **{theme}**

Requirements:
- Exactly {num_nouns} nouns and {num_verbs} verbs.
{adj_requirement}- All words should be common, practical, {level}-appropriate.
- Each noun must have: french, english, pronunciation (French IPA), article (le/la/les).
- Each verb must have: french, english, pronunciation (French IPA), past_participle \
(participe passé), auxiliary ("avoir" or "être").
- Output ONLY valid JSON, no commentary before or after.
- Use the exact schema below.

Schema example:
```json
{{
  "theme": "{theme}",
  "nouns": [
    {{"french": "maison", "english": "house", "pronunciation": "mɛzɔ̃", "article": "la"}}
  ],
  "verbs": [
    {{"french": "manger", "english": "to eat", "pronunciation": "mɑ̃ʒe", "past_participle": "mangé", "auxiliary": "avoir"}}
  ]{adj_schema}
}}
```

Now generate the complete JSON for theme "{theme}" with {count_line}.
""".strip()


def french_build_noun_practice_prompt(
    nouns: list[GeneralItem],
    lesson_number: int = 1,
) -> str:
    """Build a prompt for focused French noun introduction."""
    noun_block = _format_french_noun_list(nouns)
    return f"""\
You are a French teacher writing the noun introduction for lesson {lesson_number} \
for English-speaking learners.

NOUNS TO INTRODUCE:
{noun_block}

For each noun, produce a JSON entry with:
- french, english, pronunciation, article  (copy exactly from the list above)
- example_sentence_fr  — a short, natural French sentence using the noun (with correct article)
- example_sentence_en  — the English translation of that sentence
- memory_tip           — an English memory aid that helps remember the French word \
AND its gender/article (e.g. a similar-sounding English word, a visual image, a gender hint)

Return ONLY a raw JSON object — no markdown fences, no commentary:
{{
  "noun_items": [
    {{
      "french": "...",
      "english": "...",
      "pronunciation": "...",
      "article": "...",
      "example_sentence_fr": "...",
      "example_sentence_en": "...",
      "memory_tip": "..."
    }}
  ]
}}
""".strip()


def french_build_verb_practice_prompt(
    verbs: list[GeneralItem],
    lesson_number: int = 1,
) -> str:
    """Build a prompt for focused French verb introduction."""
    verb_block = _format_french_verb_list(verbs)
    return f"""\
You are a French teacher writing the verb introduction for lesson {lesson_number} \
for English-speaking learners.

VERBS TO INTRODUCE:
{verb_block}

For each verb, produce a JSON entry with:
- french, english, pronunciation, past_participle, auxiliary  (copy exactly from the list above)
- example_sentence_fr  — a short, natural French present-tense sentence using the verb
- example_sentence_en  — the English translation of that sentence
- memory_tip           — an English memory aid that helps remember the French verb, \
its passé composé form, and whether it takes avoir or être

Return ONLY a raw JSON object — no markdown fences, no commentary:
{{
  "verb_items": [
    {{
      "french": "...",
      "english": "...",
      "pronunciation": "...",
      "past_participle": "...",
      "auxiliary": "...",
      "example_sentence_fr": "...",
      "example_sentence_en": "...",
      "memory_tip": "..."
    }}
  ]
}}
""".strip()


def french_build_grammar_select_prompt(
    unlocked_grammar: list[GrammarItem],
    available_nouns: list[str],
    available_verbs: list[str],
    lesson_number: int,
    covered_grammar_ids: list[str],
    selection_count: int = 2,
) -> str:
    """Ask the LLM which English→French grammar point to teach next."""
    grammar_lines = "\n".join(
        f"  - id: {g.id}\n"
        f"    pattern: {g.pattern}\n"
        f"    description: {g.description}\n"
        f"    example: {g.example_source} → {g.example_target}\n"
        f"    level: {g.level}"
        for g in unlocked_grammar
    )
    noun_names = ", ".join(available_nouns)
    verb_names = ", ".join(available_verbs)
    covered_str = ", ".join(covered_grammar_ids) if covered_grammar_ids else "(none)"

    return f"""\
You are a French curriculum designer planning lesson {lesson_number} \
for English-speaking learners.

ALREADY COVERED GRAMMAR:
  {covered_str}

AVAILABLE VOCABULARY FOR THIS LESSON:
  Nouns: {noun_names}
  Verbs: {verb_names}

UNLOCKED GRAMMAR STEPS (prerequisites met, not yet taught):
{grammar_lines}

TASK:
Select exactly {selection_count} grammar IDs from the unlocked list \
(or all available if fewer than {selection_count}) that are:
1. Appropriate difficulty for lesson {lesson_number} (prefer lower level first)
2. Compatible with the available vocabulary (can form natural practice sentences)
3. If this is an early lesson, prefer level-1 steps before level-2

Return ONLY a raw JSON object — no markdown fences, no commentary:
{{
  "selected_ids": ["<id1>"],
  "rationale": "One sentence explaining why these grammar points were chosen."
}}
""".strip()


def french_build_grammar_generate_prompt(
    grammar_specs: list[GrammarItem],
    nouns: list[GeneralItem],
    verbs: list[GeneralItem],
    persons: list[tuple[str, str, str]] | None = None,
    sentences_per_grammar: int = 3,
    narrative: str = "",
) -> str:
    """Generate French practice sentences with English translations."""
    persons = persons or FRENCH_PERSONS
    grammar_block = "\n".join(
        f"  [{g.id}] {g.pattern} — {g.description}\n"
        f"  Example: {g.example_source} → {g.example_target}"
        for g in grammar_specs
    )
    noun_block = _format_french_noun_list(nouns)
    verb_block = _format_french_verb_list(verbs)
    person_lines = "\n".join(
        f"  - {en}: {fr} (IPA: {ipa})" for en, fr, ipa in persons
    )
    total = len(grammar_specs) * sentences_per_grammar
    narrative_block = (
        f"\nNARRATIVE CONTEXT:\n{narrative.strip()}\n"
        if narrative and narrative.strip()
        else ""
    )

    return f"""\
You are a French teacher writing practice sentences for English-speaking learners.

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
For each grammar point, generate {sentences_per_grammar} natural French sentences \
using the vocabulary above. Cover different persons across the sentences.
Total: {total} sentences.
If narrative context is provided, keep the sentence set consistent with that story arc.

Each sentence must include:
- grammar_id   — which grammar point this sentence practises
- french       — natural French sentence
- english      — correct English translation
- pronunciation — IPA or rough phonetic guide for the French sentence
- person       — which person (I / You / He / She / We / They)
- notes        — brief grammar note in English (e.g. verb group, agreement rule)

Return ONLY a raw JSON object — no markdown fences, no commentary:
{{
  "sentences": [
    {{
      "grammar_id": "...",
      "french": "...",
      "english": "...",
      "pronunciation": "...",
      "person": "...",
      "notes": "..."
    }}
  ]
}}
""".strip()


def french_build_sentence_review_prompt(
    sentences: list[Sentence],
    nouns: list[GeneralItem],
    verbs: list[GeneralItem],
    grammar_specs: list[GrammarItem],
) -> str:
    """Review French sentences for correctness and naturalness."""
    sentence_lines = "\n".join(
        f"  [{i}] grammar: {s.grammar_id}\n"
        f"       EN: {s.source.display_text}\n"
        f"       FR: {s.target.display_text}\n"
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
You are a native French speaker and language expert reviewing practice sentences \
created for English-speaking learners.

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
Rate each sentence on a 1-5 scale for naturalness:
  5 = Perfectly natural — a native speaker would say this
  4 = Natural enough — slightly textbook-ish but acceptable
  3 = Borderline — grammatically correct but feels forced
  2 = Unnatural — awkward word or grammar combination
  1 = Nonsensical — the words do not fit this grammar pattern

CONTENT SAFETY — MANDATORY:
Every sentence MUST be free of sexual, violent, drug-related, politically charged,
or culturally offensive content. Rewrite any such sentence to score 1.

For any sentence scoring BELOW 3, provide a revised version that:
- Uses the SAME grammar pattern (grammar_id stays the same)
- Uses vocabulary from the available pool (may swap nouns/verbs for better fit)
- Keeps the same person where possible
- Is natural and correct French

If a sentence scores 3 or above, set "revised_sentence" to null.

Return ONLY a raw JSON object — no markdown fences, no commentary:
{{
  "reviews": [
    {{
      "index": 0,
      "score": 5,
      "issue": null,
      "revised_sentence": null
    }}
  ]
}}
""".strip()


# ---------------------------------------------------------------------------
# PromptInterface adapter
# ---------------------------------------------------------------------------

class EngFrPrompts(PromptInterface):
    """PromptInterface implementation for the eng-fre language pair."""

    def build_grammar_select_prompt(
        self,
        unlocked_grammar: list[GrammarItem],
        available_nouns: list[str],
        available_verbs: list[str],
        lesson_number: int,
        covered_grammar_ids: list[str],
        selection_count: int = 2,
    ) -> str:
        return french_build_grammar_select_prompt(
            unlocked_grammar=unlocked_grammar,
            available_nouns=available_nouns,
            available_verbs=available_verbs,
            lesson_number=lesson_number,
            covered_grammar_ids=covered_grammar_ids,
            selection_count=selection_count,
        )

    def build_narrative_vocab_extract_prompt(
        self,
        narrative_blocks: list[str],
        nouns_per_block: int,
        verbs_per_block: int,
    ) -> str:
        return build_narrative_vocab_extract_prompt(
            narrative_blocks=narrative_blocks,
            source_language_label="English",
            nouns_per_block=nouns_per_block,
            verbs_per_block=verbs_per_block,
        )

    def build_grammar_generate_prompt(
        self,
        grammar_specs: list[GrammarItem],
        nouns: list[GeneralItem],
        verbs: list[GeneralItem],
        persons: list[tuple[str, str, str]] | None = None,
        sentences_per_grammar: int = 3,
        narrative: str = "",
    ) -> str:
        return french_build_grammar_generate_prompt(
            grammar_specs=grammar_specs,
            nouns=nouns,
            verbs=verbs,
            persons=persons,
            sentences_per_grammar=sentences_per_grammar,
            narrative=narrative,
        )

    def build_sentence_review_prompt(
        self,
        sentences: list[Sentence],
        nouns: list[GeneralItem],
        verbs: list[GeneralItem],
        grammar_specs: list[GrammarItem],
    ) -> str:
        return french_build_sentence_review_prompt(
            sentences=sentences,
            nouns=nouns,
            verbs=verbs,
            grammar_specs=grammar_specs,
        )

    def build_noun_practice_prompt(
        self,
        noun_items: list[GeneralItem],
        lesson_number: int,
    ) -> str:
        return french_build_noun_practice_prompt(
            nouns=noun_items,
            lesson_number=lesson_number,
        )

    def build_verb_practice_prompt(
        self,
        verb_items: list[GeneralItem],
        lesson_number: int,
    ) -> str:
        return french_build_verb_practice_prompt(
            verbs=verb_items,
            lesson_number=lesson_number,
        )
