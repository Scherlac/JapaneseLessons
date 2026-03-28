"""
English-Japanese prompt builders.

All functions return plain-text or JSON-schema prompt strings for the eng-jap
language pair.  Consumed by EngJapPrompts (the PromptInterface adapter) and
directly by legacy call sites.
"""

from __future__ import annotations

from typing import Optional

from ..models import GeneralItem, GrammarItem, Sentence
from ._base import (
    PromptInterface,
    build_narrative_generator_prompt,
    build_narrative_vocab_extract_prompt,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PERSONS_BEGINNER = [
    ("I",      "私",    "watashi"),
    ("You",    "あなた",  "anata"),
    ("He/She", "彼/彼女", "kare/kanojo"),
]

GRAMMAR_PATTERNS_BEGINNER = [
    {
        "name": "A is B",
        "structure": "A は B です (A wa B desu)",
        "description": "Identity / description sentence",
    },
    {
        "name": "Action",
        "structure": "A は B を V ます (A wa B o V-masu)",
        "description": "Subject does verb to object",
    },
    {
        "name": "Existence",
        "structure": "A に B が あります/います (A ni B ga arimasu/imasu)",
        "description": "There is B at/in A",
    },
]

DIMENSIONS_BEGINNER = {
    "tense": ["present", "past"],
    "polarity": ["affirmative", "negative"],
}

_VOCAB_EXAMPLE = """{
  "theme": "food",
  "nouns": [
    {"english": "water", "japanese": "みず", "kanji": "水", "romaji": "mizu"}
  ],
  "verbs": [
    {"english": "to eat", "japanese": "たべる", "kanji": "食べる", "romaji": "taberu", "type": "る-verb", "masu_form": "食べます"}
  ],
  "adjectives": [
    {"english": "small", "japanese": "ちいさい", "kanji": "小さい", "romaji": "chiisai", "type": "い-adj"}
  ],
  "others": [
    {"english": "hello", "japanese": "こんにちは", "kanji": "今日は", "romaji": "konnichiwa", "category": "expression"}
  ]
}"""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _format_noun_list(nouns: list[GeneralItem]) -> str:
    lines = []
    for i, n in enumerate(nouns, 1):
        kanji = n.target.extra.get("kanji", "")
        romaji = n.target.pronunciation or ""
        lines.append(f"  {i}. {n.source.display_text} — {kanji} ({n.target.display_text}, {romaji})")
    return "\n".join(lines)


def _format_verb_list(verbs: list[GeneralItem]) -> str:
    lines = []
    for i, v in enumerate(verbs, 1):
        kanji = v.target.extra.get("kanji", "")
        romaji = v.target.pronunciation or ""
        verb_type = v.target.extra.get("type", "")
        masu_form = v.target.extra.get("masu_form", "")
        lines.append(
            f"  {i}. {v.source.display_text} — {kanji} ({v.target.display_text}, {romaji}) "
            f"[{verb_type}] → polite: {masu_form}"
        )
    return "\n".join(lines)


def _build_combination_instruction(
    persons: list[tuple[str, str, str]],
    dimensions: dict,
) -> str:
    tenses = dimensions.get("tense", ["present"])
    polarities = dimensions.get("polarity", ["affirmative"])
    lines = []
    for label, *_ in persons:
        for tense in tenses:
            for polarity in polarities:
                lines.append(f"    - {label} / {tense} / {polarity}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public builders
# ---------------------------------------------------------------------------

def build_lesson_prompt(
    theme: str,
    nouns: list[dict],
    verbs: list[dict],
    persons: list[tuple[str, str, str]] | None = None,
    grammar_patterns: list[dict] | None = None,
    dimensions: dict | None = None,
    noun_reps: int = 5,
    verb_reps: int = 5,
    grammar_reps: int = 3,
) -> str:
    """Build a complete LLM instruction prompt for one lesson unit."""
    persons = persons or PERSONS_BEGINNER
    grammar_patterns = grammar_patterns or GRAMMAR_PATTERNS_BEGINNER
    dimensions = dimensions or DIMENSIONS_BEGINNER

    noun_block = _format_noun_list(nouns)
    verb_block = _format_verb_list(verbs)
    person_block = "\n".join(f"  - {label}: {jp} ({romaji})" for label, jp, romaji in persons)
    pattern_block = "\n".join(
        f"  {i}. **{p['name']}**: {p['structure']} — {p['description']}"
        for i, p in enumerate(grammar_patterns, 1)
    )
    dim_block = "\n".join(
        f"  - {dim.capitalize()}: {', '.join(vals)}"
        for dim, vals in dimensions.items()
    )
    noun_total = len(nouns) * noun_reps
    verb_total = len(verbs) * verb_reps
    grammar_sentences = (
        len(grammar_patterns)
        * len(persons)
        * len(dimensions.get("tense", ["present"]))
        * len(dimensions.get("polarity", ["affirmative"]))
    )
    grammar_total = grammar_sentences * grammar_reps

    return f"""\
You are a Japanese language teacher creating a structured lesson unit.

=== LESSON THEME: {theme.upper()} ===

Generate a complete lesson following the exact structure below.
Use ONLY the provided vocabulary. Do NOT add extra words.

--- VOCABULARY ---

NOUNS ({len(nouns)} items):
{noun_block}

VERBS ({len(verbs)} items):
{verb_block}

--- LESSON STRUCTURE ---

## PHASE 1 — NOUNS

For EACH of the {len(nouns)} nouns, produce this repetition cycle ({noun_reps} touches per noun, {noun_total} total):

  1. [INTRODUCE]   Show: English → Japanese (kanji + kana + romaji)
  2. [RECALL]       Show: Japanese → English (learner recalls the meaning)
  3. [REINFORCE]    Show: English → Japanese (confirm again)
  4. [SELF-CHECK]   Show: Japanese → Japanese (kana → kanji, or kanji → kana)
  5. [LOCK-IN]      Show: English → Japanese (final repetition)

Format each touch as:
  > **[INTRODUCE]** water → 水 (みず, mizu)

## PHASE 2 — VERBS

Same repetition cycle as Phase 1 for each of the {len(verbs)} verbs ({verb_reps} touches each, {verb_total} total).
Include the polite ます-form in every touch.

## PHASE 3 — GRAMMAR

Grammar dimensions to cover:
{dim_block}

Persons:
{person_block}

Grammar patterns:
{pattern_block}

For EACH grammar pattern, generate a sentence for EVERY combination of:
  person × tense × polarity = {grammar_sentences} sentences total

That means for each pattern:
{_build_combination_instruction(persons, dimensions)}

Repetition cycle per sentence ({grammar_reps} touches):
  1. [TRANSLATE]  English → Japanese
  2. [COMPREHEND] Japanese → English
  3. [REINFORCE]  English → Japanese

Use nouns and verbs from the vocabulary above in the sentences.

--- OUTPUT FORMAT ---

Use Markdown. Use clear headings for each phase and sub-section.
Number every single item so the learner can track progress.

Total expected touches: {noun_total} + {verb_total} + {grammar_total} = {noun_total + verb_total + grammar_total}

Begin the lesson now.
"""


def build_narrative_vocab_generate_prompt(
    nouns: list[str],
    verbs: list[str],
    theme: str,
) -> str:
    """Build a prompt to generate full Japanese vocab entries for a list of English terms."""
    noun_lines = "\n".join(f"  {i + 1}. {n}" for i, n in enumerate(nouns))
    verb_lines = "\n".join(f"  {i + 1}. {v}" for i, v in enumerate(verbs))
    total = len(nouns) + len(verbs)
    return f"""\
You are a Japanese language expert building vocabulary for a beginner lesson about "{theme}".

Generate Japanese translations for exactly the following English words.

NOUNS ({len(nouns)}):
{noun_lines}

VERBS ({len(verbs)}):
{verb_lines}

Rules:
- Output exactly {total} entries — one per word above, in the same order.
- Each noun entry must have: english, japanese (kana), kanji, romaji.
- Each verb entry must have: english, japanese (kana), kanji, romaji,
  type (one of "る-verb", "う-verb", "irregular", "な-adj"), masu_form.
- Use beginner-appropriate, natural vocabulary.
- Output ONLY a raw JSON object in this exact schema:
{{
  "theme": "{theme}",
  "nouns": [
    {{"english": "...", "japanese": "...", "kanji": "...", "romaji": "..."}}
  ],
  "verbs": [
    {{"english": "...", "japanese": "...", "kanji": "...", "romaji": "...", "type": "...", "masu_form": "..."}}
  ]
}}
""".strip()


def build_vocab_prompt(
    theme: str,
    num_nouns: int = 12,
    num_verbs: int = 10,
    num_adjectives: int = 0,
    total_words: Optional[int] = None,
    min_nouns: int = 0,
    min_verbs: int = 0,
    min_adjectives: int = 0,
    avoid_source_words: Optional[list[str]] = None,
    avoid_target_words: Optional[list[str]] = None,
    high_repeat_words: Optional[list[str]] = None,
    level: str = "beginner",
) -> str:
    """Build an LLM prompt that asks for a new vocabulary JSON file."""
    prompt = f"""\
You are a Japanese language expert building vocabulary lists for {level}-level learners.

Generate a JSON vocabulary file for the theme: **{theme}**

Requirements:
- Target output size: {num_nouns + num_verbs + num_adjectives} words total.
- Target mix:  {num_nouns} nouns, {num_verbs} verbs, {num_adjectives} adjectives.
- All words should be common, practical, {level}-appropriate.
- Include a mix of verb types: る-verbs (ichidan), う-verbs (godan), and irregulars (する/来る compounds) where natural.
- Each noun must have: english, japanese (kana), kanji, romaji.
- Each verb must have: english, japanese (kana), kanji, romaji, type ("る-verb", "う-verb", "irregular", or "な-adj"), masu_form.
- The "type" field must be exactly one of: "る-verb", "う-verb", "irregular", "な-adj".
- Each adjective must have: english, japanese (kana), kanji, romaji, type ("い-adj" or "な-adj").
- Minimum guarantees to satisfy:
  - nouns >= {min_nouns}
  - verbs >= {min_verbs}
  - adjectives >= {min_adjectives}
- You may include an optional "others" array for useful words that do not fit noun/verb/adjective cleanly.
- If "others" is present, each item should include: english, japanese (kana), kanji, romaji, and optional category.
- Output ONLY valid JSON, no commentary before or after.
- Use the exact schema below.

Schema example:
```json
{_VOCAB_EXAMPLE}
```

Now generate the complete JSON for theme "{theme}".
"""
    if avoid_source_words:
        src_list = "\n".join(f"  - {w}" for w in avoid_source_words[:200])
        prompt += (
            "\nAvoid reusing these existing source-language words "
            "(already in this theme):\n"
            f"{src_list}\n"
        )
    if avoid_target_words:
        tar_list = "\n".join(f"  - {w}" for w in avoid_target_words[:200])
        prompt += (
            "\nAvoid reusing these existing target-language words/translations:\n"
            f"{tar_list}\n"
        )
    if high_repeat_words:
        rep_list = "\n".join(f"  - {w}" for w in high_repeat_words[:100])
        prompt += (
            "\nThese words were repeated too often in previous attempts. "
            "Prefer fresh alternatives:\n"
            f"{rep_list}\n"
        )
    if total_words is not None:
        prompt += (
            f"\nRequested overall total: {total_words} words. "
            "Respect the minimum guarantees while aiming for the target mix.\n"
        )
    return prompt


def build_noun_practice_prompt(nouns: list[GeneralItem], lesson_number: int = 1) -> str:
    """Build a prompt for an LLM to generate focused noun introduction content."""
    noun_block = _format_noun_list(nouns)
    return f"""\
You are a Japanese language teacher writing a noun introduction for lesson {lesson_number}.

NOUNS TO INTRODUCE:
{noun_block}

For each noun, produce a JSON entry with:
- english, japanese (kana), kanji, romaji  (copy from the list above exactly)
- example_sentence_jp  — a short, natural Japanese sentence using the noun
- example_sentence_en  — the English translation of that sentence
- memory_tip           — a mnemonic or visual association to help remember the word

Return ONLY a raw JSON object — no markdown fences, no commentary:
{{
  "noun_items": [
    {{
      "english": "...",
      "japanese": "...",
      "kanji": "...",
      "romaji": "...",
      "example_sentence_jp": "...",
      "example_sentence_en": "...",
      "memory_tip": "..."
    }}
  ]
}}
""".strip()


def build_verb_practice_prompt(verbs: list[GeneralItem], lesson_number: int = 1) -> str:
    """Build a prompt for an LLM to generate focused verb introduction content."""
    verb_block = _format_verb_list(verbs)
    return f"""\
You are a Japanese language teacher writing a verb introduction for lesson {lesson_number}.

VERBS TO INTRODUCE:
{verb_block}

For each verb, produce a JSON entry with:
- english, japanese (kana), kanji, romaji, masu_form  (copy exactly from the list)
- polite_forms — object with four keys: present_aff, present_neg, past_aff, past_neg
- example_sentence_jp  — a short, natural Japanese sentence using the verb
- example_sentence_en  — the English translation
- memory_tip           — a mnemonic or association

Return ONLY a raw JSON object — no markdown fences, no commentary:
{{
  "verb_items": [
    {{
      "english": "...",
      "japanese": "...",
      "kanji": "...",
      "romaji": "...",
      "masu_form": "...",
      "polite_forms": {{
        "present_aff": "...",
        "present_neg": "...",
        "past_aff": "...",
        "past_neg": "..."
      }},
      "example_sentence_jp": "...",
      "example_sentence_en": "...",
      "memory_tip": "..."
    }}
  ]
}}
""".strip()


def build_grammar_select_prompt(
    unlocked_grammar: list[GrammarItem],
    available_nouns: list[GeneralItem],
    available_verbs: list[GeneralItem],
    lesson_number: int,
    covered_grammar_ids: list[str],
    selection_count: int = 2,
) -> str:
    """Level-1 grammar prompt: ask the LLM which grammar point to teach next."""
    grammar_lines = "\n".join(
        f"  - id: {g.id}\n"
        f"    structure: {g.pattern}\n"
        f"    description: {g.description}\n"
        f"    example: {g.example_source} → {g.example_target}\n"
        f"    level: {g.level}"
        for g in unlocked_grammar
    )
    noun_names = ", ".join(n.source.display_text for n in available_nouns)
    verb_names = ", ".join(v.source.display_text for v in available_verbs)
    covered_str = ", ".join(covered_grammar_ids) if covered_grammar_ids else "(none)"

    return f"""\
You are a Japanese curriculum designer planning lesson {lesson_number}.

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


def build_grammar_generate_prompt(
    grammar_specs: list[GrammarItem],
    nouns: list[GeneralItem],
    verbs: list[GeneralItem],
    persons: list[tuple[str, str, str]] | None = None,
    sentences_per_grammar: int = 3,
    narrative: str = "",
) -> str:
    """Level-2 grammar prompt: generate example sentences for selected grammar."""
    _default_persons = [("I", "私", "watashi"), ("You", "あなた", "anata"), ("He/She", "彼", "kare")]
    persons = persons or _default_persons

    grammar_block = "\n".join(
        f"  [{g.id}] {g.pattern} — {g.description}\n"
        f"  Example: {g.example_source} → {g.example_target}"
        for g in grammar_specs
    )
    noun_block = _format_noun_list(nouns)
    verb_block = _format_verb_list(verbs)
    person_lines = "\n".join(f"  - {en} ({jp}, {rm})" for en, jp, rm in persons)
    total = len(grammar_specs) * sentences_per_grammar
    narrative_block = (
        f"\nNARRATIVE CONTEXT:\n{narrative.strip()}\n"
        if narrative and narrative.strip()
        else ""
    )

    return f"""\
You are a Japanese language teacher generating practice sentences.

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
For each grammar point, generate {sentences_per_grammar} natural sentences using the
vocabulary above. Cover different persons across the sentences.
Use polite (ます/です) form throughout. Total: {total} sentences.
If narrative context is provided, keep the sentence set consistent with that story arc.

Each sentence must include:
- grammar_id  — which grammar point this sentence demonstrates
- english     — natural English
- japanese    — correct Japanese in polite form (kanji + kana)
- romaji      — romanised transcription
- person      — which person (I / You / He/She / etc.)
- notes       — brief grammar note (e.g. which particle, which conjugation)

Return ONLY a raw JSON object — no markdown fences, no commentary:
{{
  "sentences": [
    {{
      "grammar_id": "...",
      "english": "...",
      "japanese": "...",
      "romaji": "...",
      "person": "...",
      "notes": "..."
    }}
  ]
}}
""".strip()


def build_content_validate_prompt(sentences: list[dict]) -> str:
    """Cross-check prompt: ask the LLM to validate and correct Japanese sentences."""
    sentence_lines = "\n".join(
        f"  [{i}] EN: {s.get('english', '')}\n"
        f"       JP: {s.get('japanese', '')}\n"
        f"       RM: {s.get('romaji', '')}"
        for i, s in enumerate(sentences)
    )

    return f"""\
You are a native Japanese language expert reviewing learning material.

SENTENCES TO VALIDATE:
{sentence_lines}

TASK:
Review each sentence for accuracy. Check:
1. Correct Japanese particles (は, を, が, に, へ, etc.)
2. Correct polite conjugation (ます/ません/ました/ませんでした)
3. Natural word order (SOV)
4. Correct romaji transcription
5. Faithful English translation

For each error found, provide a correction entry with your fix and explanation.
If a sentence is correct, do NOT include it in the corrections list.

Return ONLY a raw JSON object — no markdown fences, no commentary:
{{
  "score": <0-10 overall accuracy>,
  "corrections": [
    {{
      "index": <sentence index>,
      "original_japanese": "...",
      "corrected_japanese": "...",
      "original_romaji": "...",
      "corrected_romaji": "...",
      "explanation": "...",
      "severity": "minor|major"
    }}
  ],
  "summary": "One-sentence overall assessment."
}}
""".strip()


def build_sentence_review_prompt(
    sentences: list[Sentence],
    nouns: list[GeneralItem],
    verbs: list[GeneralItem],
    grammar_specs: list[GrammarItem],
) -> str:
    """Review prompt: ask the LLM to rate sentences for naturalness and rewrite poor ones."""
    sentence_lines = "\n".join(
        f"  [{i}] grammar: {s.grammar_id}\n"
        f"       EN: {s.source.display_text}\n"
        f"       JP: {s.target.display_text}\n"
        f"       RM: {s.target.pronunciation}\n"
        f"       Person: {s.grammar_parameters.get('person', '')}"
        for i, s in enumerate(sentences)
    )
    grammar_block = "\n".join(
        f"  [{g.id}] {g.pattern} — {g.description}"
        for g in grammar_specs
    )
    noun_names = ", ".join(
        f"{n.source.display_text} ({n.target.extra.get('kanji', n.target.display_text)})"
        for n in nouns
    )
    verb_names = ", ".join(
        f"{v.source.display_text} ({v.target.extra.get('kanji', v.target.display_text)})"
        for v in verbs
    )

    return f"""\
You are a native Japanese language expert reviewing practice sentences for naturalness.

These sentences were generated by combining vocabulary and grammar patterns independently.
Some combinations may be awkward, forced, or nonsensical. Your job is to identify and fix them.

GRAMMAR PATTERNS USED:
{grammar_block}

AVAILABLE VOCABULARY:
  Nouns: {noun_names}
  Verbs: {verb_names}

SENTENCES TO REVIEW:
{sentence_lines}

TASK:
For each sentence, rate its naturalness from 1 to 5:
  5 = Perfectly natural — a native speaker would say this
  4 = Natural enough — slightly textbook-ish but acceptable
  3 = Borderline — grammatically correct but feels forced
  2 = Unnatural — awkward combination of words/grammar
  1 = Nonsensical — the words don't fit this grammar pattern at all

For any sentence scoring BELOW 3, provide a revised version that:
- Uses the SAME grammar pattern (grammar_id stays the same)
- Uses vocabulary from the available pool above (may swap nouns/verbs for better fit)
- Keeps the same person where possible
- Is natural and something a native speaker would actually say
- Stays in polite (ます/です) form

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
      "issue": "Existence pattern does not pair naturally with action verb 'to eat'",
      "revised_sentence": {{
        "grammar_id": "...",
        "english": "...",
        "japanese": "...",
        "romaji": "...",
        "person": "...",
        "notes": "..."
      }}
    }}
  ],
  "overall_naturalness": <1-5 average score>
}}
""".strip()


# ---------------------------------------------------------------------------
# PromptInterface adapter
# ---------------------------------------------------------------------------

class EngJapPrompts(PromptInterface):
    """Prompt builders for English-Japanese lessons."""

    def build_grammar_select_prompt(
        self,
        unlocked_grammar: list[GrammarItem],
        available_nouns: list[GeneralItem],
        available_verbs: list[GeneralItem],
        lesson_number: int,
        covered_grammar_ids: list[str],
        selection_count: int = 2,
    ) -> str:
        return build_grammar_select_prompt(
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
            source_language_label="English",
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
        return build_narrative_vocab_generate_prompt(nouns, verbs, theme)

    def build_grammar_generate_prompt(
        self,
        grammar_specs: list[GrammarItem],
        nouns: list[GeneralItem],
        verbs: list[GeneralItem],
        persons: list[tuple[str, str, str]] | None = None,
        sentences_per_grammar: int = 3,
        narrative: str = "",
    ) -> str:
        return build_grammar_generate_prompt(
            grammar_specs, nouns, verbs, persons, sentences_per_grammar, narrative,
        )

    def build_sentence_review_prompt(
        self,
        sentences: list[Sentence],
        nouns: list[GeneralItem],
        verbs: list[GeneralItem],
        grammar_specs: list[GrammarItem],
    ) -> str:
        return build_sentence_review_prompt(sentences, nouns, verbs, grammar_specs)

    def build_noun_practice_prompt(
        self,
        noun_items: list[GeneralItem],
        lesson_number: int,
    ) -> str:
        return build_noun_practice_prompt(noun_items, lesson_number)

    def build_verb_practice_prompt(
        self,
        verb_items: list[GeneralItem],
        lesson_number: int,
    ) -> str:
        return build_verb_practice_prompt(verb_items, lesson_number)
