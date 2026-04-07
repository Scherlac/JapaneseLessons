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
- Each block should be 2-4 short, vivid sentences that capture a meaningful
  scene or story beat.
- Write in {canonical_language}, using simple, clear vocabulary suitable for
  a language-learning lesson context.
- Make each block feel like a natural story continuation, not a list of facts.
- If seed blocks are provided, weave them into the appropriate positions.

Return ONLY a raw JSON object:
{{
    "blocks": [
        {{
            "index": 1,
            "narrative": "...",
            "alignment_notes": "A brief note on tone or scene context for the teacher.",
            "sentiment": "One-word tone label, e.g. heartwarming, tense, playful, melancholic."
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
Create a narrative progression with {lesson_blocks} blocks.
Each block should be 2-4 short sentences of story context.
Keep the overall situation coherent, but make each block meaningfully different.
The progression should stay concrete and {level_details}.

Return ONLY a raw JSON object:
{{
    "blocks": [
        {{
            "index": 1,
            "narrative": "...",
            "alignment_notes": "A backstory for the same scene (different angle, simpler vocabulary, or avoiding spoilers for later events).",
            "sentiment": "One-word tone label, e.g. heartwarming, tense, playful, melancholic."
        }}
    ]
}}
""".strip()
