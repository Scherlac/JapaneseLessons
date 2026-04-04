"""Prompt builder for resolving canonical items into language-specific content."""

from __future__ import annotations

import json
from typing import Any

from jlesson.language_config._base import PartialLanguageConfig
from jlesson.models import CanonicalItem, Phase


def _format_field_hints(config: PartialLanguageConfig | None, label: str) -> str:
    """Return a formatted block of per-field instructions for the LLM."""
    if not config or not config.llm_content_hints:
        return ""
    lines = "\n".join(f"  - {hint}" for hint in config.llm_content_hints)
    return f"{label} field requirements:\n{lines}"


def build_item_resolve_prompt(
    *,
    source_language: str,
    target_language: str,
    canonical_language: str,
    block_index: int,
    narrative_content: str,
    grammar_ids: list[str],
    content_sequences: dict[Phase, list[CanonicalItem]],
    source_config: PartialLanguageConfig | None = None,
    target_config: PartialLanguageConfig | None = None,
) -> str:
    """Build a prompt that resolves canonical (English) items into a target language pair.

    The LLM receives the canonical items grouped by phase (nouns, verbs, etc.)
    and must return fully populated source/target pairs with pronunciation,
    display text, TTS text, and any language-specific extra fields.
    """
    items_by_phase: dict[str, list[dict[str, Any]]] = {}
    for phase, items in content_sequences.items():
        phase_key = phase.value if isinstance(phase, Phase) else str(phase)
        items_by_phase[phase_key] = [
            {"id": item.id, "text": item.text, "gloss": item.gloss}
            for item in items
        ]

    payload = json.dumps(items_by_phase, indent=2, ensure_ascii=False)

    source_hints = _format_field_hints(source_config, f"{source_language} (source)")
    target_hints = _format_field_hints(target_config, f"{target_language} (target)")
    lang_hints_section = "\n\n".join(filter(None, [source_hints, target_hints]))
    if lang_hints_section:
        lang_hints_section = f"\nLANGUAGE-SPECIFIC FIELD REQUIREMENTS:\n{lang_hints_section}\n"

    # Build the target JSON template dynamically from target_config extras
    target_extra_template = ""
    if target_config and target_config.extra_display_keys:
        extra_fields = ", ".join(
            f'"{k}": "..."' for k in target_config.extra_display_keys
        )
        target_extra_template = f',\n    "extra": {{{extra_fields}}}'

    return f"""\
You are a language lesson content generator.

TASK: Resolve the following canonical ({canonical_language}) vocabulary items
into full {source_language} \u2194 {target_language} lesson items.

BLOCK {block_index} \u2014 NARRATIVE CONTEXT:
{narrative_content}

GRAMMAR POINTS FOR THIS BLOCK: {', '.join(grammar_ids) if grammar_ids else '(none)'}
{lang_hints_section}
CANONICAL ITEMS (grouped by phase):
{payload}

For EACH item return a JSON object with these fields:
- "id": same id as the input
- "phase": the phase key (e.g. "nouns", "verbs", "grammar")
- "source": {{
    "display_text": "{source_language} display form",
    "tts_text": "spoken form for TTS",
    "pronunciation": "phonetic guide"
  }}
- "target": {{
    "display_text": "{target_language} display form",
    "tts_text": "spoken form for TTS",
    "pronunciation": "phonetic reading"{target_extra_template}
  }}
- "canonical": {{
    "id": same id,
    "text": original canonical text,
    "gloss": original gloss
  }}

IMPORTANT:
- Populate every required field for every item — do not leave fields empty.
- Follow the language-specific field requirements above exactly.
- For target extra fields, include only those that are applicable to the item's phase
  (e.g. masu_form is for verbs only).
- Return a JSON object with a single key "items" containing the flat list of all resolved items.
- Do NOT include any commentary outside the JSON.
"""

