from __future__ import annotations


def build_subtitle_narrative_prompt(
    script: str,
    lesson_blocks: int,
    canonical_language: str,
    seed_blocks: list[str] | None = None,
) -> str:
    """Build a prompt that asks the LLM to synthesise N narrative blocks from
    a full subtitle/screenplay script.

    Used when the user provides an SRT file whose dialogue length is very
    different from the requested number of lesson blocks.
    """
    seed_lines = "\n".join(
        f"  - Block {index}: {text}"
        for index, text in enumerate(seed_blocks or [], 1)
        if text.strip()
    ) or "  (none)"

    # Truncate script to ~12 000 chars to fit context windows comfortably
    # while still covering a full episode of typical length.
    script_excerpt = script if len(script) <= 12_000 else script[:12_000] + "\n[... remainder omitted ...]"

    return f"""\
You are a curriculum writer adapting a movie or TV-show script into engaging
language-learning story blocks.

SCRIPT (extracted subtitle dialogue):
---
{script_excerpt}
---

TARGET BLOCK COUNT:
    {lesson_blocks}

WRITE EACH BLOCK NARRATIVE IN THE FOLLOWING LANGUAGE:
    {canonical_language}

OPTIONAL USER-PROVIDED SEED BLOCKS (incorporate these if supplied):
{seed_lines}

TASK:
Read the full script above and create a coherent progression of {lesson_blocks}
narrative blocks that cover the story arc from start to finish.

Guidelines:
- Distribute coverage evenly: early blocks summarise early events, later blocks
  cover later events.
- Each block should be 2-4 short, vivid sentences in {canonical_language}.
- VARY THE STYLE across blocks. A block can be any of:
    * a vivid scene summary (what happens and how it feels)
    * a short dialogue fragment — quote a key exchange almost word-for-word,
      then briefly explain its significance
    * a joke or comic reversal — set up the situation, deliver the punchline
    * an emotional beat — capture the feeling of a decisive or moving moment
  Mixing styles keeps learners engaged and mirrors how real storytelling works.
- Make each block feel self-contained but part of a flowing whole.
- Use simple, clear vocabulary suitable for a language-learning context.
- If seed blocks are provided, weave them into the appropriate positions.
- ENGAGEMENT: identify the most memorable or emotionally charged moments in
  the script — iconic lines, turning points, comic scenes, high-emotion beats.
  Give each such moment its own block and write it vividly. Use the
  alignment_notes to flag why it is a highlight ("iconic line",
  "emotional peak", "comic reversal") and fill engagement_note with a direct
  instruction for the lesson planner (e.g. "Iconic line: Joel discovers he
  cannot leave — use vocabulary of obligation; ideal to introduce a grammar
  point expressing constraint or inevitability.").

Return ONLY a raw JSON object:
{{
    "blocks": [
        {{
            "index": 1,
            "narrative": "...",
            "alignment_notes": "A brief note on tone or scene context for the teacher.",
            "sentiment": "One-word tone label, e.g. heartwarming, tense, playful, melancholic.",
            "engagement_note": "If this is a memorable or emotionally charged moment (iconic dialogue, turning point, comic reversal, emotional peak), write one direct instruction sentence for the lesson planner, e.g. 'Iconic line: Joel learns he cannot leave — prioritise vocabulary of obligation and shock; ideal block to introduce a grammar point for expressing constraint or inevitability.' Leave empty string for ordinary blocks."
        }}
    ]
}}
""".strip()


def build_narrative_generator_prompt(
    theme: str,
    level_details: str,
    lesson_blocks: int,
    canonical_language: str,
    seed_blocks: list[str] | None = None,
) -> str:
    """Build a language-agnostic narrative generation prompt."""
    seed_lines = "\n".join(
        f"  - Block {index}: {text}"
        for index, text in enumerate(seed_blocks or [], 1)
        if text.strip()
    ) or "  (none)"

    return f"""\
You are a curriculum writer, planning a {level_details} lesson narrative.

THEME:
    {theme}

TARGET BLOCK COUNT:
    {lesson_blocks}

WRITE THE BLOCK NARRATIVE IN FOLLOWING LANGUAGE:
    {canonical_language}

OPTIONAL USER-PROVIDED SEED BLOCKS:
{seed_lines}

TASK:
Create a progression of {lesson_blocks} varied scene blocks in {canonical_language}.
Each block is 2-4 sentences and can take different forms: a vivid scene
summary, a short dialogue fragment (quote a key exchange and explain it),
a joke or comic reversal (setup + punchline), or an emotional beat.
Vary the style across the lesson to keep learners engaged.
The progression should suit {level_details} learners and stay coherent.
ENGAGEMENT: identify the most memorable or emotionally charged moments —
turning points, comic scenes, dramatic reveals, iconic lines. Give each
highlight its own block, write it vividly, flag it in alignment_notes, and
fill engagement_note with a direct planner instruction (see field description).

Return ONLY a raw JSON object:
{{
    "blocks": [
        {{
            "index": 1,
            "narrative": "...",
            "alignment_notes": "A backstory for the same scene (different angle, simpler vocabulary, or avoiding spoilers for later events).",
            "sentiment": "One-word tone label, e.g. heartwarming, tense, playful, melancholic.",
            "engagement_note": "If this is a memorable or emotionally charged moment (iconic dialogue, turning point, comic reversal, emotional peak), write one direct instruction sentence for the lesson planner, e.g. 'Iconic line: Joel learns he cannot leave — prioritise vocabulary of obligation and shock; ideal block to introduce a grammar point for expressing constraint or inevitability.' Leave empty string for ordinary blocks."
        }}
    ]
}}
""".strip()
