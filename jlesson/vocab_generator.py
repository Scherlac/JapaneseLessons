"""
Vocabulary Generator

Calls the LLM to generate a complete vocabulary JSON file for a given theme.
Validates the schema and saves the result to vocab/<theme>.json.

This is the actual generation step — compare with build_vocab_prompt() in
prompt_template.py, which only builds the text prompt without calling the LLM.

Usage:
    from vocab_generator import generate_vocab
    vocab = generate_vocab("animals")          # saves to vocab/animals.json
    vocab = generate_vocab("school", save=False)  # dry-run, no file written

CLI (via generate_lesson.py):
    python generate_lesson.py --create-vocab animals
    python generate_lesson.py --create-vocab school --nouns 15 --verbs 12
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from .llm_client import ask_llm_json_free
from .prompt_template import build_vocab_prompt

VOCAB_DIR = Path(__file__).parent.parent / "vocab"

_REQUIRED_NOUN_FIELDS = {"english", "japanese", "kanji", "romaji"}
_REQUIRED_VERB_FIELDS = {"english", "japanese", "kanji", "romaji", "type", "masu_form"}
_VALID_VERB_TYPES = {"る-verb", "う-verb", "irregular", "な-adj"}

_REQUIRED_HUN_NOUN_FIELDS = {"english", "hungarian", "pronunciation"}
_REQUIRED_HUN_VERB_FIELDS = {"english", "hungarian", "pronunciation", "past_tense"}


# ── Schema validation ─────────────────────────────────────────────────────────

def validate_vocab_schema(vocab: dict) -> list[str]:
    """Validate a vocab dict against the required schema.

    Returns a list of human-readable error strings.
    An empty list means the vocab is valid.
    """
    errors: list[str] = []

    if "theme" not in vocab:
        errors.append("Missing top-level 'theme' field")

    nouns = vocab.get("nouns")
    if not isinstance(nouns, list) or len(nouns) == 0:
        errors.append("'nouns' must be a non-empty list")
    else:
        for i, noun in enumerate(nouns):
            missing = _REQUIRED_NOUN_FIELDS - set(noun.keys())
            if missing:
                errors.append(
                    f"nouns[{i}] ({noun.get('english', '?')!r}): "
                    f"missing fields {sorted(missing)}"
                )

    verbs = vocab.get("verbs")
    if not isinstance(verbs, list) or len(verbs) == 0:
        errors.append("'verbs' must be a non-empty list")
    else:
        for i, verb in enumerate(verbs):
            missing = _REQUIRED_VERB_FIELDS - set(verb.keys())
            if missing:
                errors.append(
                    f"verbs[{i}] ({verb.get('english', '?')!r}): "
                    f"missing fields {sorted(missing)}"
                )
                continue  # can't check type if fields are missing
            if verb["type"] not in _VALID_VERB_TYPES:
                errors.append(
                    f"verbs[{i}] ({verb['english']!r}): "
                    f"invalid type {verb['type']!r} — "
                    f"must be one of {sorted(_VALID_VERB_TYPES)}"
                )

    return errors


def validate_hungarian_vocab_schema(vocab: dict) -> list[str]:
    """Validate a Hungarian vocab dict against the required schema.

    Returns a list of human-readable error strings.
    An empty list means the vocab is valid.
    """
    errors: list[str] = []

    if "theme" not in vocab:
        errors.append("Missing top-level 'theme' field")

    nouns = vocab.get("nouns")
    if not isinstance(nouns, list) or len(nouns) == 0:
        errors.append("'nouns' must be a non-empty list")
    else:
        for i, noun in enumerate(nouns):
            missing = _REQUIRED_HUN_NOUN_FIELDS - set(noun.keys())
            if missing:
                errors.append(
                    f"nouns[{i}] ({noun.get('english', '?')!r}): "
                    f"missing fields {sorted(missing)}"
                )

    verbs = vocab.get("verbs")
    if not isinstance(verbs, list) or len(verbs) == 0:
        errors.append("'verbs' must be a non-empty list")
    else:
        for i, verb in enumerate(verbs):
            missing = _REQUIRED_HUN_VERB_FIELDS - set(verb.keys())
            if missing:
                errors.append(
                    f"verbs[{i}] ({verb.get('english', '?')!r}): "
                    f"missing fields {sorted(missing)}"
                )

    return errors


# ── Main generator ────────────────────────────────────────────────────────────

def generate_vocab(
    theme: str,
    num_nouns: int = 12,
    num_verbs: int = 10,
    level: str = "beginner",
    save: bool = True,
    output_dir: Optional[Path] = None,
) -> dict:
    """Generate vocabulary JSON for a theme using the LLM.

    Builds a vocab prompt, calls the LLM, validates the schema, and
    optionally saves the result to disk.

    Args:
        theme: Vocabulary theme, e.g. "animals", "school", "weather".
        num_nouns: Target noun count (default 12).
        num_verbs: Target verb count (default 10).
        level: Difficulty — "beginner", "intermediate", "advanced".
        save: If True (default), write the result to vocab/<theme>.json.
        output_dir: Directory to write the file (defaults to vocab/).

    Returns:
        The validated vocab dict (always has 'theme', 'nouns', 'verbs').

    Raises:
        ValueError: If the LLM response fails schema validation.
        Exception: Re-raises LLM connection/timeout errors.
    """
    prompt = build_vocab_prompt(
        theme=theme,
        num_nouns=num_nouns,
        num_verbs=num_verbs,
        level=level,
    )

    print(f"Generating vocab for '{theme}' ({num_nouns} nouns, {num_verbs} verbs, {level})…")
    raw = ask_llm_json_free(prompt)

    # LLM sometimes omits the 'theme' field — inject it
    if "theme" not in raw:
        raw["theme"] = theme

    # Strip leading/trailing whitespace from all string values (LLMs sometimes pad them)
    for group in ("nouns", "verbs"):
        for item in raw.get(group, []):
            if isinstance(item, dict):
                for k, v in item.items():
                    if isinstance(v, str):
                        item[k] = v.strip()

    errors = validate_vocab_schema(raw)
    if errors:
        raise ValueError(
            f"LLM-generated vocab for '{theme}' failed schema validation:\n"
            + "\n".join(f"  • {e}" for e in errors)
        )

    if save:
        out_dir = Path(output_dir) if output_dir else VOCAB_DIR
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{theme}.json"
        out_path.write_text(
            json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(
            f"Saved: {out_path}  "
            f"({len(raw['nouns'])} nouns, {len(raw['verbs'])} verbs)"
        )

    return raw
