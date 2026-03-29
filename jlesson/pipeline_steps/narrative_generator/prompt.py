from __future__ import annotations


def build_narrative_generator_prompt(
    theme: str,
    lesson_number: int,
    lesson_blocks: int,
    source_language_label: str,
    seed_blocks: list[str] | None = None,
) -> str:
    """Build a language-agnostic narrative generation prompt."""
    seed_lines = "\n".join(
        f"  - Block {index}: {text}"
        for index, text in enumerate(seed_blocks or [], 1)
        if text.strip()
    ) or "  (none)"

    return f"""\
You are a curriculum writer planning a beginner-friendly lesson narrative.

THEME:
    {theme}

LESSON NUMBER:
    {lesson_number}

TARGET BLOCK COUNT:
    {lesson_blocks}

WRITE THE BLOCK NARRATIVE IN:
    {source_language_label}

OPTIONAL USER-PROVIDED SEED BLOCKS:
{seed_lines}

TASK:
Create a narrative progression with {lesson_blocks} blocks.
Each block should be 2-4 short sentences of story context.
Keep the overall situation coherent, but make each block meaningfully different.
The progression should stay concrete and beginner-friendly.

Return ONLY a raw JSON object:
{{
    "blocks": [
        {{"index": 1, "narrative": "..."}}
    ]
}}
""".strip()
