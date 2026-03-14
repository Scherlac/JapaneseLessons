"""
Prompt templates for generating Japanese lesson instructions.

Each function returns a plain-text prompt string that can be sent to an LLM.
Templates are kept as simple f-strings — no templating engine needed (KISS).
"""


def _format_noun_list(nouns: list[dict]) -> str:
    """Format noun list into a readable block for the prompt."""
    lines = []
    for i, n in enumerate(nouns, 1):
        lines.append(f"  {i}. {n['english']} — {n['kanji']} ({n['japanese']}, {n['romaji']})")
    return "\n".join(lines)


def _format_verb_list(verbs: list[dict]) -> str:
    """Format verb list into a readable block for the prompt."""
    lines = []
    for i, v in enumerate(verbs, 1):
        lines.append(
            f"  {i}. {v['english']} — {v['kanji']} ({v['japanese']}, {v['romaji']}) "
            f"[{v['type']}] → polite: {v['masu_form']}"
        )
    return "\n".join(lines)


PERSONS_BEGINNER = [
    ("I", "私 (watashi)"),
    ("You", "あなた (anata)"),
    ("He/She", "彼/彼女 (kare/kanojo)"),
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


def build_lesson_prompt(
    theme: str,
    nouns: list[dict],
    verbs: list[dict],
    persons: list[tuple[str, str]] | None = None,
    grammar_patterns: list[dict] | None = None,
    dimensions: dict | None = None,
    noun_reps: int = 5,
    verb_reps: int = 5,
    grammar_reps: int = 3,
) -> str:
    """
    Build a complete LLM instruction prompt for one lesson unit.

    Returns a plain-text prompt ready to be sent to any LLM.
    """
    persons = persons or PERSONS_BEGINNER
    grammar_patterns = grammar_patterns or GRAMMAR_PATTERNS_BEGINNER
    dimensions = dimensions or DIMENSIONS_BEGINNER

    noun_block = _format_noun_list(nouns)
    verb_block = _format_verb_list(verbs)

    person_block = "\n".join(f"  - {label}: {jp}" for label, jp in persons)

    pattern_block = "\n".join(
        f"  {i}. **{p['name']}**: {p['structure']} — {p['description']}"
        for i, p in enumerate(grammar_patterns, 1)
    )

    dim_block = "\n".join(
        f"  - {dim.capitalize()}: {', '.join(vals)}"
        for dim, vals in dimensions.items()
    )

    # Calculate totals
    noun_total = len(nouns) * noun_reps
    verb_total = len(verbs) * verb_reps
    grammar_sentences = len(grammar_patterns) * len(persons) * len(dimensions.get("tense", ["present"])) * len(dimensions.get("polarity", ["affirmative"]))
    grammar_total = grammar_sentences * grammar_reps

    prompt = f"""\
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
    return prompt


def _build_combination_instruction(
    persons: list[tuple[str, str]],
    dimensions: dict,
) -> str:
    """Build a human-readable list of all person × dimension combos."""
    tenses = dimensions.get("tense", ["present"])
    polarities = dimensions.get("polarity", ["affirmative"])

    lines = []
    for label, _ in persons:
        for tense in tenses:
            for polarity in polarities:
                lines.append(f"    - {label} / {tense} / {polarity}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Vocabulary generation prompt
# ---------------------------------------------------------------------------

_VOCAB_EXAMPLE = """{
  "theme": "food",
  "nouns": [
    {"english": "water", "japanese": "みず", "kanji": "水", "romaji": "mizu"}
  ],
  "verbs": [
    {"english": "to eat", "japanese": "たべる", "kanji": "食べる", "romaji": "taberu", "type": "る-verb", "masu_form": "食べます"}
  ]
}"""


def build_vocab_prompt(
    theme: str,
    num_nouns: int = 12,
    num_verbs: int = 10,
    level: str = "beginner",
) -> str:
    """
    Build an LLM prompt that asks for a new vocabulary JSON file.

    The output from the LLM can be saved directly as vocab/<theme>.json.
    """
    prompt = f"""\
You are a Japanese language expert building vocabulary lists for {level}-level learners.

Generate a JSON vocabulary file for the theme: **{theme}**

Requirements:
- Exactly {num_nouns} nouns and {num_verbs} verbs.
- All words should be common, practical, {level}-appropriate.
- Include a mix of verb types: る-verbs (ichidan), う-verbs (godan), and irregulars (する/来る compounds) where natural.
- Each noun must have: english, japanese (kana), kanji, romaji.
- Each verb must have: english, japanese (kana), kanji, romaji, type ("る-verb", "う-verb", "irregular", or "な-adj"), masu_form.
- The "type" field must be exactly one of: "る-verb", "う-verb", "irregular", "な-adj".
- Output ONLY valid JSON, no commentary before or after.
- Use the exact schema below.

Schema example:
```json
{_VOCAB_EXAMPLE}
```

Now generate the complete JSON for theme "{theme}" with {num_nouns} nouns and {num_verbs} verbs.
"""
    return prompt
