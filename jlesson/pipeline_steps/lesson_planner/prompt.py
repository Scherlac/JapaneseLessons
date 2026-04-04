"""Prompt builder for resolving canonical items into language-specific content."""

from __future__ import annotations

import json
from typing import Any

from jlesson.models import CanonicalItem, Phase


def build_item_resolve_prompt(
    *,
    source_language: str,
    target_language: str,
    canonical_language: str,
    block_index: int,
    narrative_content: str,
    grammar_ids: list[str],
    content_sequences: dict[Phase, list[CanonicalItem]],
) -> str:
    """Build a prompt that resolves canonical (English) items into a target language pair.

    The LLM receives the canonical items grouped by phase (nouns, verbs, etc.)
    and must return fully populated source/target pairs with pronunciation,
    display text, and TTS text for each item.
    """
    items_by_phase: dict[str, list[dict[str, Any]]] = {}
    for phase, items in content_sequences.items():
        phase_key = phase.value if isinstance(phase, Phase) else str(phase)
        items_by_phase[phase_key] = [
            {"id": item.id, "text": item.text, "gloss": item.gloss}
            for item in items
        ]

    payload = json.dumps(items_by_phase, indent=2, ensure_ascii=False)

    return f"""\
You are a language lesson content generator.

TASK: Resolve the following canonical ({canonical_language}) vocabulary items
into full {source_language} ↔ {target_language} lesson items.

BLOCK {block_index} — NARRATIVE CONTEXT:
{narrative_content}

GRAMMAR POINTS FOR THIS BLOCK: {', '.join(grammar_ids) if grammar_ids else '(none)'}

CANONICAL ITEMS (grouped by phase):
{payload}

For EACH item, return a JSON object with these fields:
- "id": same id as the input
- "phase": the phase key (e.g. "nouns", "verbs")
- "source": {{
    "text": "{source_language} word/phrase",
    "display_text": "display form",
    "tts_text": "text-to-speech form",
    "pronunciation": "phonetic guide if applicable"
  }}
- "target": {{
    "text": "{target_language} word/phrase",
    "display_text": "display form",
    "tts_text": "text-to-speech form",
    "pronunciation": "phonetic reading (e.g. hiragana for Japanese)"
  }}
- "canonical": {{
    "id": same id,
    "text": original canonical text,
    "gloss": original gloss
  }}

Return a JSON object with a single key "items" containing the flat list of all resolved items.
Do NOT include any commentary outside the JSON.
"""
