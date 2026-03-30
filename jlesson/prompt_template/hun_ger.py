"""
Hungarian-German prompt builders.

All functions return plain-text or JSON-schema prompt strings for the hun-ger
language pair.  Consumed by HunGerPrompts (the PromptInterface adapter) and
directly by legacy call sites.

Target audience: Hungarian-speaking children (ages 8-12) learning German.
All instructions and memory tips are in Hungarian.

NOTE — Narrative texts are supplied in the *canonical* language (English).
Vocabulary extraction prompts therefore ask the LLM to read English narrative
blocks, but the vocabulary generation step produces Hungarian + German entries.
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

GERMAN_PERSONS: list[tuple[str, str, str]] = [
    ("ich",  "én",        "ɪç"),
    ("du",   "te",        "duː"),
    ("er",   "ő (fiú)",   "eːɐ̯"),
    ("sie",  "ő (lány)",  "ziː"),
    ("wir",  "mi",        "viːɐ̯"),
    ("sie",  "ők",        "ziː"),
]

GERMAN_GRAMMAR_PATTERNS: list[dict] = [
    {
        "name": "Subjekt + Verb + Objekt",
        "pattern": "S + V + O",
        "description": "Alapmondat — alany + ige + tárgy",
    },
    {
        "name": "Subjekt + sein + Nomen/Adjektiv",
        "pattern": "S + sein + N/Adj",
        "description": "Létige — alany + sein + főnév/melléknév",
    },
    {
        "name": "Es gibt + Akkusativ",
        "pattern": "Es gibt + Akk",
        "description": "Létezés — Van valami valahol",
    },
]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _format_german_noun_list(nouns: list[GeneralItem]) -> str:
    lines = []
    for i, n in enumerate(nouns, 1):
        article = n.target.extra.get("article", "")
        article_prefix = f"{article} " if article else ""
        lines.append(
            f"  {i}. {article_prefix}{n.target.display_text} — {n.source.display_text} "
            f"(Aussprache: {n.target.pronunciation})"
        )
    return "\n".join(lines)


def _format_german_verb_list(verbs: list[GeneralItem]) -> str:
    lines = []
    for i, v in enumerate(verbs, 1):
        partizip = v.target.extra.get("partizip_ii", "?")
        hilfsverb = v.target.extra.get("hilfsverb", "haben")
        lines.append(
            f"  {i}. {v.target.display_text} — {v.source.display_text} "
            f"(Aussprache: {v.target.pronunciation}) → Partizip II: {partizip} "
            f"(Hilfsverb: {hilfsverb})"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public builders
# ---------------------------------------------------------------------------

def german_build_lesson_prompt(
    theme: str,
    nouns: list[dict],
    verbs: list[dict],
    persons: list[tuple[str, str, str]] | None = None,
    grammar_patterns: list[dict] | None = None,
    noun_reps: int = 5,
    verb_reps: int = 5,
    grammar_reps: int = 3,
) -> str:
    """Build a complete lesson prompt for Hungarian children learning German."""
    persons = persons or GERMAN_PERSONS
    grammar_patterns = grammar_patterns or GERMAN_GRAMMAR_PATTERNS

    noun_block = _format_german_noun_list(nouns)
    verb_block = _format_german_verb_list(verbs)
    person_block = "\n".join(
        f"  - {de}: {hu} (Aussprache: {pron})" for de, hu, pron in persons
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
Du bist ein Deutschlehrer, der ungarischen Kindern im Alter von 8-12 Jahren Deutsch beibringt.

=== LEKTIONSTHEMA: {theme.upper()} ===

Erstelle eine vollständige Lektion nach der unten stehenden Struktur.
Verwende NUR das vorgegebene Vokabular. Füge KEINE zusätzlichen Wörter hinzu.
Alle Erklärungen sollen auf Ungarisch sein; Zielsprach-Beispiele auf Deutsch.

--- WORTSCHATZ ---

NOMEN ({len(nouns)} Wörter):
{noun_block}

VERBEN ({len(verbs)} Wörter):
{verb_block}

--- LEKTIONSSTRUKTUR ---

## TEIL 1 — NOMEN

Für JEDES Nomen {noun_reps} Wiederholungen erzeugen ({noun_total} insgesamt):

  1. [EINFÜHREN]     Ungarisch → Deutsch (mit Aussprache und Artikel)
  2. [ABRUFEN]       Deutsch → Ungarisch (Schüler erinnert sich an die Bedeutung)
  3. [FESTIGEN]      Ungarisch → Deutsch (nochmals bestätigen)
  4. [PRÜFEN]        Deutscher Satz mit dem Wort
  5. [VERANKERN]     Ungarisch → Deutsch (letzte Wiederholung)

## TEIL 2 — VERBEN

Gleicher Wiederholungszyklus für jedes Verb ({verb_reps} Wiederholungen, {verb_total} insgesamt).
Für jedes Verb auch das Partizip II und das Hilfsverb zeigen.

## TEIL 3 — GRAMMATIK

Personen:
{person_block}

Grammatikmuster:
{pattern_block}

Für jedes Muster Sätze mit verschiedenen Personen generieren.
Wiederholungszyklus pro Satz ({grammar_reps} Wiederholungen):
  1. [ÜBERSETZEN]    Ungarisch → Deutsch
  2. [VERSTEHEN]     Deutsch → Ungarisch
  3. [FESTIGEN]      Ungarisch → Deutsch

Verwende in den Sätzen nur den oben aufgeführten Wortschatz.

--- AUSGABEFORMAT ---

Verwende Markdown. Verwende klare Überschriften für jeden Teil und Abschnitt.
Nummeriere jeden Eintrag, damit der Schüler den Fortschritt verfolgen kann.

Gesamtwiederholungen: {noun_total} + {verb_total} + {grammar_total} = {noun_total + verb_total + grammar_total}

Beginne jetzt mit der Lektion.
"""


def german_build_vocab_prompt(
    theme: str,
    num_nouns: int = 12,
    num_verbs: int = 10,
    num_adjectives: int = 0,
    level: str = "beginner",
) -> str:
    """Build an LLM prompt that asks for a Hungarian-German vocabulary JSON file."""
    adj_requirement = (
        f"- Exactly {num_adjectives} adjectives.\n"
        "- Each adjective must have: german, hungarian, pronunciation (German IPA).\n"
        if num_adjectives > 0 else ""
    )
    count_line = f"{num_nouns} nouns and {num_verbs} verbs"
    if num_adjectives > 0:
        count_line += f" and {num_adjectives} adjectives"
    adj_schema = (
        ',\n  "adjectives": [\n    {"german": "groß", "hungarian": "nagy", "pronunciation": "ɡʁoːs"}\n  ]'
        if num_adjectives > 0 else ""
    )
    return f"""\
You are a German language teacher creating a vocabulary list for Hungarian children aged 8-12.

Generate a JSON vocabulary file for the theme: **{theme}**

Requirements:
- Exactly {num_nouns} nouns and {num_verbs} verbs.
{adj_requirement}- All words should be common, practical, {level}-appropriate, and suitable for children.
- Each noun must have: german, hungarian, pronunciation (German IPA), article (der/die/das).
- Each verb must have: german, hungarian, pronunciation (German IPA), partizip_ii \
(the German past participle), hilfsverb ("haben" or "sein").
- Output ONLY valid JSON, no commentary before or after.
- Use the exact schema below.

Schema example:
```json
{{
  "theme": "{theme}",
  "nouns": [
    {{"german": "Hund", "hungarian": "kutya", "pronunciation": "hʊnt", "article": "der"}}
  ],
  "verbs": [
    {{"german": "essen", "hungarian": "enni", "pronunciation": "ˈɛsn̩", "partizip_ii": "gegessen", "hilfsverb": "haben"}}
  ]{adj_schema}
}}
```

Now generate the complete JSON for theme "{theme}" with {count_line}.
""".strip()


def german_build_narrative_vocab_generate_prompt(
    nouns: list[str],
    verbs: list[str],
    theme: str,
) -> str:
    """Build a prompt to generate Hungarian-German vocab entries for narrative terms.

    The input nouns/verbs are in English (canonical narrative language).
    The LLM must translate them into both Hungarian AND German.
    """
    noun_lines = "\n".join(f"  {i + 1}. {n}" for i, n in enumerate(nouns))
    verb_lines = "\n".join(f"  {i + 1}. {v}" for i, v in enumerate(verbs))
    total = len(nouns) + len(verbs)
    return f"""\
You are a language expert building vocabulary for a Hungarian children's lesson about "{theme}".

The following words were extracted from an English narrative text.
Provide BOTH the Hungarian AND the German translations plus German pronunciation.

ENGLISH NOUNS ({len(nouns)}):
{noun_lines}

ENGLISH VERBS ({len(verbs)}):
{verb_lines}

Rules:
- Output exactly {total} entries — one per word above, in the same order.
- Each noun entry must have: english (the original), german, hungarian,
  pronunciation (German IPA), article (der/die/das).
- Each verb entry must have: english (the original), german, hungarian,
  pronunciation (German IPA), partizip_ii (the German past participle),
  hilfsverb ("haben" or "sein").
- Use beginner-appropriate vocabulary suitable for children aged 8-12.
- For German nouns always capitalise the first letter (e.g. "Hund", not "hund").
- Output ONLY a raw JSON object in this exact schema:
{{
  "theme": "{theme}",
  "nouns": [
    {{"english": "...", "german": "...", "hungarian": "...", "pronunciation": "...", "article": "der|die|das"}}
  ],
  "verbs": [
    {{"english": "...", "german": "...", "hungarian": "...", "pronunciation": "...", "partizip_ii": "...", "hilfsverb": "haben|sein"}}
  ]
}}
""".strip()


def german_build_noun_practice_prompt(
    nouns: list[GeneralItem],
    lesson_number: int = 1,
) -> str:
    """Build a prompt for an LLM to generate focused noun introduction content."""
    noun_block = _format_german_noun_list(nouns)
    return f"""\
You are a German teacher writing the noun introduction for lesson {lesson_number}, \
aimed at Hungarian children aged 8-12.

NOUNS TO INTRODUCE:
{noun_block}

For each noun, produce a JSON entry with:
- german, hungarian, pronunciation, article  (copy exactly from the list above)
- example_sentence_de  — a short, natural German sentence using the noun (with correct article)
- example_sentence_hu  — the Hungarian translation of that sentence
- memory_tip           — a memory aid written in Hungarian that helps remember \
the German word AND its article (e.g. a similar-sounding Hungarian word, a visual \
image, a gender mnemonic)

The memory_tip should be creative and child-friendly — use Hungarian words or \
concepts that an 8-12 year old would know. Include a tip for remembering the \
article (der/die/das) when possible.

Return ONLY a raw JSON object — no markdown fences, no commentary:
{{
  "noun_items": [
    {{
      "german": "...",
      "hungarian": "...",
      "pronunciation": "...",
      "article": "...",
      "example_sentence_de": "...",
      "example_sentence_hu": "...",
      "memory_tip": "..."
    }}
  ]
}}
""".strip()


def german_build_verb_practice_prompt(
    verbs: list[GeneralItem],
    lesson_number: int = 1,
) -> str:
    """Build a prompt for an LLM to generate focused verb introduction content."""
    verb_block = _format_german_verb_list(verbs)
    return f"""\
You are a German teacher writing the verb introduction for lesson {lesson_number}, \
aimed at Hungarian children aged 8-12.

VERBS TO INTRODUCE:
{verb_block}

For each verb, produce a JSON entry with:
- german, hungarian, pronunciation, partizip_ii, hilfsverb  (copy exactly from the list above)
- example_sentence_de  — a short, natural German sentence using the verb (Präsens)
- example_sentence_hu  — the Hungarian translation of that sentence
- memory_tip           — a memory aid written in Hungarian that helps remember \
the German verb and its Partizip II form

The memory_tip should briefly explain:
- For regular verbs (e.g. spielen → gespielt): "ge- + tő + -t szabály!"
- For irregular verbs (e.g. essen → gegessen): give a fun tip about the irregular form
- For sein-verbs (e.g. laufen → gelaufen): mention that Perfekt uses "sein"

Tips must be in Hungarian and child-friendly — use words and analogies \
that an 8-12 year old Hungarian child would understand.

Return ONLY a raw JSON object — no markdown fences, no commentary:
{{
  "verb_items": [
    {{
      "german": "...",
      "hungarian": "...",
      "pronunciation": "...",
      "partizip_ii": "...",
      "hilfsverb": "...",
      "example_sentence_de": "...",
      "example_sentence_hu": "...",
      "memory_tip": "..."
    }}
  ]
}}
""".strip()


def german_build_grammar_select_prompt(
    unlocked_grammar: list[GrammarItem],
    available_nouns: list[GeneralItem],
    available_verbs: list[GeneralItem],
    lesson_number: int,
    covered_grammar_ids: list[str],
    selection_count: int = 2,
) -> str:
    """Ask the LLM which Hungarian→German grammar point to teach next."""
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
    covered_str = ", ".join(covered_grammar_ids) if covered_grammar_ids else "(nincs még)"

    return f"""\
You are a German curriculum designer planning lesson {lesson_number} \
for Hungarian children aged 8-12.

ALREADY COVERED GRAMMAR:
  {covered_str}

AVAILABLE VOCABULARY FOR THIS LESSON:
  Nouns: {noun_names}
  Verbs: {verb_names}

UNLOCKED GRAMMAR STEPS (prerequisites met, not yet taught):
{grammar_lines}

TASK:
Select exactly {selection_count} grammar IDs from the unlocked list (or all available if fewer than {selection_count}) that are:
1. Appropriate difficulty for lesson {lesson_number} (prefer lower level first)
2. Compatible with the available vocabulary (can form natural practice sentences)
3. If this is an early lesson, prefer level-1 steps before level-2
4. Consider German-specific challenges for Hungarian speakers \
(article–case agreement, word order in subordinate clauses, separable verbs)

Return ONLY a raw JSON object — no markdown fences, no commentary:
{{
  "selected_ids": ["<id1>"],
  "rationale": "One sentence explaining why these grammar points were chosen."
}}
""".strip()


def german_build_grammar_generate_prompt(
    grammar_specs: list[GrammarItem],
    nouns: list[GeneralItem],
    verbs: list[GeneralItem],
    persons: list[tuple[str, str, str]] | None = None,
    sentences_per_grammar: int = 3,
    narrative: str = "",
) -> str:
    """Generate German practice sentences with Hungarian translations."""
    persons = persons or GERMAN_PERSONS

    grammar_block = "\n".join(
        f"  [{g.id}] {g.pattern} — {g.description}\n"
        f"  Példa: {g.example_source} → {g.example_target}"
        for g in grammar_specs
    )
    noun_block = _format_german_noun_list(nouns)
    verb_block = _format_german_verb_list(verbs)
    person_lines = "\n".join(
        f"  - {de}: {hu} (Aussprache: {pron})" for de, hu, pron in persons
    )
    total = len(grammar_specs) * sentences_per_grammar
    narrative_block = (
        f"\nNARRATIVE CONTEXT (in English — adapt content to German target sentences):\n"
        f"{narrative.strip()}\n"
        if narrative and narrative.strip()
        else ""
    )

    return f"""\
You are a German teacher writing practice sentences for Hungarian children aged 8-12.

GRAMMAR POINTS TO PRACTICE:
{grammar_block}

VOCABULARY TO USE (use only these words):
Nomen:
{noun_block}

Verben:
{verb_block}

PERSONEN:
{person_lines}
{narrative_block}

TASK:
For each grammar point, generate {sentences_per_grammar} natural German sentences \
using the vocabulary above. Cover different persons across the sentences.
Total: {total} sentences.
If narrative context is provided (in English), adapt the story ideas into German \
sentences — do NOT simply translate the English literally; create natural German \
sentences that fit the narrative theme.

IMPORTANT German-specific rules:
- Use correct articles and case endings (Nominativ, Akkusativ, Dativ as required)
- Place the verb correctly (V2 in main clauses, verb-final in subordinate clauses)
- For separable verbs, split correctly in main clauses

Each sentence must include:
- grammar_id  — which grammar point this sentence practises
- german      — natural German sentence
- hungarian   — correct Hungarian translation
- person      — which person (ich / du / er / sie / wir / sie)
- notes       — brief grammar note in German (e.g. which tense, which case, word order)

Return ONLY a raw JSON object — no markdown fences, no commentary:
{{
  "sentences": [
    {{
      "grammar_id": "...",
      "german": "...",
      "hungarian": "...",
      "person": "...",
      "notes": "..."
    }}
  ]
}}
""".strip()


def german_build_sentence_review_prompt(
    sentences: list[Sentence],
    nouns: list[GeneralItem],
    verbs: list[GeneralItem],
    grammar_specs: list[GrammarItem],
) -> str:
    """Review German sentences for correctness and age-appropriateness."""
    sentence_lines = "\n".join(
        f"  [{i}] grammar: {s.grammar_id}\n"
        f"       DE: {s.target.display_text}\n"
        f"       HU: {s.source.display_text}\n"
        f"       Person: {s.grammar_parameters.get('person', '')}"
        for i, s in enumerate(sentences)
    )
    grammar_block = "\n".join(
        f"  [{g.id}] {g.pattern} — {g.description}"
        for g in grammar_specs
    )
    noun_names = ", ".join(
        f"{n.target.extra.get('article', '')} {n.target.display_text} ({n.source.display_text})"
        for n in nouns
    )
    verb_names = ", ".join(
        f"{v.target.display_text} ({v.source.display_text})" for v in verbs
    )

    return f"""\
You are a native German language expert reviewing practice sentences \
created for Hungarian children aged 8-12.

These sentences were generated by combining vocabulary and grammar patterns independently.
Some combinations may be forced or unnatural. \
Your job is to identify and fix such sentences.

Pay special attention to:
- Article-case agreement (der/den/dem, die/der, das/dem)
- Verb position (V2 in main clauses, verb-final in Nebensätze)
- Separable verb prefix placement
- Natural word order and idiomatic phrasing

GRAMMAR PATTERNS USED:
{grammar_block}

AVAILABLE VOCABULARY:
  Nomen: {noun_names}
  Verben: {verb_names}

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
- Uses correct German grammar with proper article-case agreement

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
      "issue": "Falscher Kasus — Akkusativ statt Dativ nach 'mit'",
      "revised_sentence": {{
        "grammar_id": "...",
        "german": "...",
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

class HunGerPrompts(PromptInterface):
    """Prompt builders for Hungarian-German lessons."""

    def build_grammar_select_prompt(
        self,
        unlocked_grammar: list[GrammarItem],
        available_nouns: list[GeneralItem],
        available_verbs: list[GeneralItem],
        lesson_number: int,
        covered_grammar_ids: list[str],
        selection_count: int = 2,
    ) -> str:
        return german_build_grammar_select_prompt(
            unlocked_grammar, available_nouns, available_verbs,
            lesson_number, covered_grammar_ids, selection_count,
        )

    def build_narrative_vocab_extract_prompt(
        self,
        narrative_blocks: list[str],
        nouns_per_block: int,
        verbs_per_block: int,
    ) -> str:
        # Narratives are in English (canonical language) — extract English terms
        return build_narrative_vocab_extract_prompt(
            narrative_blocks,
            source_language_label="English",
            nouns_per_block=nouns_per_block,
            verbs_per_block=verbs_per_block,
        )

    def build_narrative_vocab_generate_prompt(
        self,
        nouns: list[str],
        verbs: list[str],
        theme: str,
    ) -> str:
        return german_build_narrative_vocab_generate_prompt(nouns, verbs, theme)

    def build_grammar_generate_prompt(
        self,
        grammar_specs: list[GrammarItem],
        nouns: list[GeneralItem],
        verbs: list[GeneralItem],
        persons: list[tuple[str, str, str]] | None = None,
        sentences_per_grammar: int = 3,
        narrative: str = "",
    ) -> str:
        return german_build_grammar_generate_prompt(
            grammar_specs, nouns, verbs, persons, sentences_per_grammar, narrative,
        )

    def build_sentence_review_prompt(
        self,
        sentences: list[Sentence],
        nouns: list[GeneralItem],
        verbs: list[GeneralItem],
        grammar_specs: list[GrammarItem],
    ) -> str:
        return german_build_sentence_review_prompt(sentences, nouns, verbs, grammar_specs)

    def build_noun_practice_prompt(
        self,
        noun_items: list[GeneralItem],
        lesson_number: int,
    ) -> str:
        return german_build_noun_practice_prompt(noun_items, lesson_number)

    def build_verb_practice_prompt(
        self,
        verb_items: list[GeneralItem],
        lesson_number: int,
    ) -> str:
        return german_build_verb_practice_prompt(verb_items, lesson_number)
