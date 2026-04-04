from __future__ import annotations


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
