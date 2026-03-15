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


# ---------------------------------------------------------------------------
# Focused practice prompts (JSON-output, use with ask_llm_json_free)
# ---------------------------------------------------------------------------
# These prompts are designed for the curriculum pipeline.
# Each returns a JSON object — feed to ask_llm_json_free(), not ask_llm_json().

def build_noun_practice_prompt(nouns: list[dict], lesson_number: int = 1) -> str:
    """Build a prompt for an LLM to generate focused noun introduction content.

    Returns JSON: {"noun_items": [{"english", "japanese", "kanji", "romaji",
    "example_sentence_jp", "example_sentence_en", "memory_tip"}, ...]}

    Use with ask_llm_json_free().
    """
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


def build_verb_practice_prompt(verbs: list[dict], lesson_number: int = 1) -> str:
    """Build a prompt for an LLM to generate focused verb introduction content.

    Returns JSON: {"verb_items": [{"english", "japanese", "kanji", "romaji",
    "masu_form", "polite_forms", "example_sentence_jp", "example_sentence_en",
    "memory_tip"}, ...]}
    "polite_forms" contains all four ます-forms.

    Use with ask_llm_json_free().
    """
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
    unlocked_grammar: list[dict],
    available_nouns: list[dict],
    available_verbs: list[dict],
    lesson_number: int,
    covered_grammar_ids: list[str],
) -> str:
    """Level-1 grammar prompt: ask the LLM which grammar point to teach next.

    Given the unlocked (available but not yet covered) grammar steps and the
    current vocabulary pool, the LLM selects the most suitable 1-2 grammar
    IDs for this lesson and explains its reasoning.

    Returns JSON: {"selected_ids": [...], "rationale": "..."}

    Use with ask_llm_json_free().
    """
    grammar_lines = "\n".join(
        f"  - id: {g['id']}\n"
        f"    structure: {g['structure']}\n"
        f"    description: {g['description']}\n"
        f"    example: {g['example_en']} → {g['example_jp']}\n"
        f"    level: {g['level']}"
        for g in unlocked_grammar
    )

    noun_names = ", ".join(n["english"] for n in available_nouns)
    verb_names = ", ".join(v["english"] for v in available_verbs)
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
Select 1 OR 2 grammar IDs from the unlocked list that are:
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
    grammar_specs: list[dict],
    nouns: list[dict],
    verbs: list[dict],
    persons: list[tuple[str, str, str]] | None = None,
    sentences_per_grammar: int = 3,
) -> str:
    """Level-2 grammar prompt: generate example sentences for selected grammar.

    Given one or more grammar specs and the lesson vocabulary, the LLM produces
    natural example sentences covering different persons.

    Returns JSON: {"sentences": [{"grammar_id", "english", "japanese", "romaji",
    "person", "notes"}, ...]}

    Use with ask_llm_json_free().
    """
    _default_persons = [("I", "私", "watashi"), ("You", "あなた", "anata"), ("He/She", "彼", "kare")]
    persons = persons or _default_persons

    grammar_block = "\n".join(
        f"  [{g['id']}] {g['structure']} — {g['description']}\n"
        f"  Example: {g['example_en']} → {g['example_jp']}"
        for g in grammar_specs
    )

    noun_block = _format_noun_list(nouns)
    verb_block = _format_verb_list(verbs)

    person_lines = "\n".join(
        f"  - {en} ({jp}, {rm})" for en, jp, rm in persons
    )

    total = len(grammar_specs) * sentences_per_grammar

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

TASK:
For each grammar point, generate {sentences_per_grammar} natural sentences using the
vocabulary above. Cover different persons across the sentences.
Use polite (ます/です) form throughout. Total: {total} sentences.

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
    """Cross-check prompt: ask the LLM to validate and correct Japanese sentences.

    Accepts a list of sentence dicts with at minimum: english, japanese, romaji.
    Returns a validation report with per-sentence corrections and an overall score.

    Returns JSON: {"score": 0-10, "corrections": [...], "summary": "..."}
    Each correction: {"index", "original_japanese", "corrected_japanese",
                       "original_romaji", "corrected_romaji", "explanation", "severity"}

    Use with ask_llm_json_free().
    """
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
