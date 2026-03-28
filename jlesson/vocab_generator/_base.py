"""
Vocabulary Generator — shared orchestration and utilities.

Calls the LLM to generate a complete vocabulary JSON file for a given theme.
Language-specific schema validation lives in the eng_jap / hun_eng sibling
modules and is dispatched here by language code.

Usage:
    from jlesson.vocab_generator import generate_vocab
    vocab = generate_vocab("animals")          # saves to vocab/animals.json
    vocab = generate_vocab("school", save=False)  # dry-run, no file written
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from ..language_config import LanguageConfig, get_language_config
from ..llm_client import ask_llm_json_free
from ..prompt_template import build_vocab_prompt

VOCAB_DIR = Path(__file__).parent.parent.parent / "vocab"


def validate_vocab_schema(vocab: dict, language_config: LanguageConfig) -> list[str]:
    """Validate a vocab dict against the schema defined by *language_config*.

    Uses ``language_config.vocab_noun_fields``, ``vocab_verb_fields``,
    ``vocab_verb_types``, ``vocab_adj_fields``, and ``vocab_adj_types`` so
    that no language-pair–specific branching is needed here.

    Returns a list of human-readable error strings; empty means valid.
    """
    errors: list[str] = []

    if "theme" not in vocab:
        errors.append("Missing top-level 'theme' field")

    nouns = vocab.get("nouns")
    if not isinstance(nouns, list) or len(nouns) == 0:
        errors.append("'nouns' must be a non-empty list")
    else:
        for i, noun in enumerate(nouns):
            missing = language_config.vocab_noun_fields - set(noun.keys())
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
            missing = language_config.vocab_verb_fields - set(verb.keys())
            if missing:
                errors.append(
                    f"verbs[{i}] ({verb.get('english', '?')!r}): "
                    f"missing fields {sorted(missing)}"
                )
                continue
            if language_config.vocab_verb_types and verb["type"] not in language_config.vocab_verb_types:
                errors.append(
                    f"verbs[{i}] ({verb['english']!r}): "
                    f"invalid type {verb['type']!r} — "
                    f"must be one of {sorted(language_config.vocab_verb_types)}"
                )

    adjectives = vocab.get("adjectives")
    if adjectives is not None and language_config.vocab_adj_fields:
        if not isinstance(adjectives, list):
            errors.append("'adjectives' must be a list when provided")
        else:
            for i, adj in enumerate(adjectives):
                missing = language_config.vocab_adj_fields - set(adj.keys())
                if missing:
                    errors.append(
                        f"adjectives[{i}] ({adj.get('english', '?')!r}): "
                        f"missing fields {sorted(missing)}"
                    )
                    continue
                if language_config.vocab_adj_types and adj["type"] not in language_config.vocab_adj_types:
                    errors.append(
                        f"adjectives[{i}] ({adj['english']!r}): "
                        f"invalid type {adj['type']!r} — "
                        f"must be one of {sorted(language_config.vocab_adj_types)}"
                    )

    return errors

_MAX_NOUNS_PER_REQUEST = 120
_MAX_VERBS_PER_REQUEST = 60
_MAX_ADJECTIVES_PER_REQUEST = 60
_MAX_JSON_RETRIES = 3


def _allocate_by_weights(total: int, weights: list[float]) -> list[int]:
    """Allocate an integer total across weights using largest-remainder method."""
    if total <= 0:
        return [0 for _ in weights]
    weight_sum = sum(weights)
    if weight_sum <= 0:
        base = total // len(weights)
        extra = total % len(weights)
        return [base + (1 if i < extra else 0) for i in range(len(weights))]

    raw = [(total * w) / weight_sum for w in weights]
    floors = [int(x) for x in raw]
    remaining = total - sum(floors)
    remainders = sorted(
        ((raw[i] - floors[i], i) for i in range(len(weights))),
        reverse=True,
    )
    for _, idx in remainders[:remaining]:
        floors[idx] += 1
    return floors


def _split_counts(total: int, buckets: int) -> list[int]:
    """Split total across buckets as evenly as possible."""
    base = total // buckets
    extra = total % buckets
    return [base + (1 if i < extra else 0) for i in range(buckets)]


def _request_vocab_json(prompt: str) -> dict:
    """Request vocab JSON with a few retries when parsing fails."""
    retry_suffix = """

IMPORTANT:
- Return a single raw JSON object only.
- Do not use markdown fences.
- Do not include explanatory text.
"""
    last_error: Optional[Exception] = None
    for attempt in range(1, _MAX_JSON_RETRIES + 1):
        try:
            return ask_llm_json_free(prompt if attempt == 1 else f"{prompt}\n{retry_suffix}")
        except ValueError as e:
            last_error = e
    assert last_error is not None
    raise last_error


def _collect_items(raw: dict, key: str) -> list[dict]:
    """Safely collect list items from a model response."""
    items = raw.get(key, [])
    if isinstance(items, list):
        return [x for x in items if isinstance(x, dict)]
    return []


def _merge_unique_by_english(existing: list[dict], new_items: list[dict]) -> tuple[list[dict], int]:
    """Merge items while keeping only the first occurrence per English key."""
    merged = list(existing)
    seen = {
        str(item.get("english", "")).strip().lower()
        for item in existing
        if isinstance(item, dict) and str(item.get("english", "")).strip()
    }
    added = 0
    for item in new_items:
        key = str(item.get("english", "")).strip().lower()
        if key and key not in seen:
            seen.add(key)
            merged.append(item)
            added += 1
    return merged, added


def _resolve_word_targets(
    num_nouns: Optional[int],
    num_verbs: Optional[int],
    num_adjectives: Optional[int],
    total_count: Optional[int],
    default_nouns: int = 12,
    default_verbs: int = 10,
    default_adjectives: int = 0,
) -> tuple[int, int, int]:
    """Resolve final noun/verb/adjective targets from minimums and optional total count."""
    if total_count is None:
        nouns = default_nouns if num_nouns is None else num_nouns
        verbs = default_verbs if num_verbs is None else num_verbs
        adjectives = default_adjectives if num_adjectives is None else num_adjectives
        if nouns < 0 or verbs < 0 or adjectives < 0:
            raise ValueError("--nouns, --verbs, and --adjectives must be >= 0")
        return nouns, verbs, adjectives

    nouns_min = 0 if num_nouns is None else num_nouns
    verbs_min = 0 if num_verbs is None else num_verbs
    adjectives_min = 0 if num_adjectives is None else num_adjectives

    if nouns_min < 0 or verbs_min < 0 or adjectives_min < 0:
        raise ValueError("--nouns, --verbs, and --adjectives must be >= 0")
    if total_count < 0:
        raise ValueError("--count must be >= 0")

    min_sum = nouns_min + verbs_min + adjectives_min
    if total_count < min_sum:
        raise ValueError(
            f"--count ({total_count}) must be >= --nouns + --verbs + --adjectives ({min_sum})"
        )

    remaining = total_count - min_sum
    if remaining == 0:
        return nouns_min, verbs_min, adjectives_min

    if min_sum == 0:
        extra_nouns, extra_verbs, extra_adjectives = _allocate_by_weights(
            remaining,
            [1.0, 1.0, 1.0],
        )
    else:
        weights = [
            float(nouns_min) if num_nouns is not None else 1.0,
            float(verbs_min) if num_verbs is not None else 1.0,
            float(adjectives_min) if num_adjectives is not None else 1.0,
        ]
        extra_nouns, extra_verbs, extra_adjectives = _allocate_by_weights(remaining, weights)

    nouns = nouns_min + extra_nouns
    verbs = verbs_min + extra_verbs
    adjectives = adjectives_min + extra_adjectives
    return nouns, verbs, adjectives


def generate_vocab(
    theme: str,
    num_nouns: Optional[int] = None,
    num_verbs: Optional[int] = None,
    num_adjectives: Optional[int] = None,
    total_count: Optional[int] = None,
    level: str = "beginner",
    save: bool = True,
    allow_overwrite: bool = False,
    avoid_english_words: Optional[list[str]] = None,
    avoid_target_words: Optional[list[str]] = None,
    output_dir: Optional[Path] = None,
    language: str = "eng-jap",
) -> dict:
    """Generate vocabulary JSON for a theme using the LLM.

    Builds a vocab prompt, calls the LLM, validates the schema, and
    optionally saves the result to disk.

    Args:
        theme: Vocabulary theme, e.g. "animals", "school", "weather".
        num_nouns: Target noun count (or minimum when total_count is set).
        num_verbs: Target verb count (or minimum when total_count is set).
        num_adjectives: Target adjective count (or minimum when total_count is set).
        total_count: Optional total words target.
        level: Difficulty — "beginner", "intermediate", "advanced".
        save: If True (default), write the result to vocab/<theme>.json.
        allow_overwrite: If True, permit replacing an existing vocab file.
        avoid_english_words: Existing English words to avoid regenerating.
        avoid_target_words: Existing target-language words to avoid regenerating.
        output_dir: Directory to write the file (defaults to vocab/).
        language: Language pair code — "eng-jap" (default) or "hun-eng".

    Returns:
        The validated vocab dict (always has 'theme', 'nouns', 'verbs').
    """
    target_nouns, target_verbs, target_adjectives = _resolve_word_targets(
        num_nouns=num_nouns,
        num_verbs=num_verbs,
        num_adjectives=num_adjectives,
        total_count=total_count,
    )
    if total_count is None:
        print(
            f"Generating vocab for '{theme}' "
            f"({target_nouns} nouns, {target_verbs} verbs, {target_adjectives} adjectives, {level})..."
        )
    else:
        min_nouns = 0 if num_nouns is None else num_nouns
        min_verbs = 0 if num_verbs is None else num_verbs
        min_adjectives = 0 if num_adjectives is None else num_adjectives
        print(
            f"Generating vocab for '{theme}' "
            f"(total {total_count}; minimums: nouns>={min_nouns}, verbs>={min_verbs}, adjectives>={min_adjectives}; {level})..."
        )
        print(
            "  Planned mix target: "
            f"{target_nouns} nouns, {target_verbs} verbs, {target_adjectives} adjectives"
        )
    out_dir = Path(output_dir) if output_dir else VOCAB_DIR
    out_path = out_dir / f"{theme}.json"
    partial_out_path = out_dir / f"{theme}.partial.json"
    blocked_english = {
        str(w).strip().lower()
        for w in (avoid_english_words or [])
        if str(w).strip()
    }
    repeat_hits: set[str] = set()

    if save and out_path.exists() and not allow_overwrite:
        raise ValueError(
            f"Theme '{theme}' already exists at {out_path}. "
            "Use 'jlesson vocab extend' to add more words, "
            "or re-run 'jlesson vocab create' with --force to overwrite."
        )

    def _build_prompt(nouns_count: int, verbs_count: int, adjectives_count: int) -> str:
        if language == "hun-eng":
            from ..prompt_template import hungarian_build_vocab_prompt

            prompt = hungarian_build_vocab_prompt(
                theme=theme,
                num_nouns=nouns_count,
                num_verbs=verbs_count,
                num_adjectives=adjectives_count,
                level=level,
            )
            if blocked_english:
                src = "\n".join(f"  - {w}" for w in sorted(blocked_english)[:200])
                prompt += "\nAvoid reusing these existing English words:\n" + src + "\n"
            if avoid_target_words:
                tgt = "\n".join(f"  - {w}" for w in avoid_target_words[:200])
                prompt += "\nAvoid reusing these existing target words:\n" + tgt + "\n"
            if repeat_hits:
                rep = "\n".join(f"  - {w}" for w in sorted(repeat_hits)[:100])
                prompt += "\nThese words repeated in prior attempts; avoid them:\n" + rep + "\n"
            return prompt
        return build_vocab_prompt(
            theme=theme,
            num_nouns=nouns_count,
            num_verbs=verbs_count,
            num_adjectives=adjectives_count,
            total_words=total_count,
            min_nouns=0 if num_nouns is None else num_nouns,
            min_verbs=0 if num_verbs is None else num_verbs,
            min_adjectives=0 if num_adjectives is None else num_adjectives,
            avoid_source_words=sorted(blocked_english),
            avoid_target_words=avoid_target_words,
            high_repeat_words=sorted(repeat_hits),
            level=level,
        )

    needs_batching = (
        target_nouns > _MAX_NOUNS_PER_REQUEST
        or target_verbs > _MAX_VERBS_PER_REQUEST
        or target_adjectives > _MAX_ADJECTIVES_PER_REQUEST
    )

    if not needs_batching:
        raw = _request_vocab_json(_build_prompt(target_nouns, target_verbs, target_adjectives))
        if "theme" not in raw:
            raw["theme"] = theme
    else:
        batches = max(
            (target_nouns + _MAX_NOUNS_PER_REQUEST - 1) // _MAX_NOUNS_PER_REQUEST,
            (target_verbs + _MAX_VERBS_PER_REQUEST - 1) // _MAX_VERBS_PER_REQUEST,
            (target_adjectives + _MAX_ADJECTIVES_PER_REQUEST - 1) // _MAX_ADJECTIVES_PER_REQUEST,
        )
        noun_targets = _split_counts(target_nouns, batches)
        verb_targets = _split_counts(target_verbs, batches)
        adjective_targets = _split_counts(target_adjectives, batches)

        raw = {"theme": theme, "nouns": [], "verbs": [], "adjectives": []}
        seen_nouns: set[str] = set(blocked_english)
        seen_verbs: set[str] = set(blocked_english)
        seen_adjectives: set[str] = set(blocked_english)

        for idx, (n_target, v_target, a_target) in enumerate(
            zip(noun_targets, verb_targets, adjective_targets),
            start=1,
        ):
            if n_target <= 0 and v_target <= 0 and a_target <= 0:
                continue
            print(
                f"  Batch {idx}/{batches}: requesting "
                f"{n_target} nouns, {v_target} verbs, {a_target} adjectives..."
            )
            batch = _request_vocab_json(_build_prompt(n_target, v_target, a_target))

            for noun in _collect_items(batch, "nouns"):
                key = str(noun.get("english", "")).strip().lower()
                if key and key not in seen_nouns:
                    seen_nouns.add(key)
                    raw["nouns"].append(noun)
                elif key:
                    repeat_hits.add(key)

            for verb in _collect_items(batch, "verbs"):
                key = str(verb.get("english", "")).strip().lower()
                if key and key not in seen_verbs:
                    seen_verbs.add(key)
                    raw["verbs"].append(verb)
                elif key:
                    repeat_hits.add(key)

            for adj in _collect_items(batch, "adjectives"):
                key = str(adj.get("english", "")).strip().lower()
                if key and key not in seen_adjectives:
                    seen_adjectives.add(key)
                    raw["adjectives"].append(adj)
                elif key:
                    repeat_hits.add(key)

        for round_idx in range(1, 4):
            missing_n = target_nouns - len(raw["nouns"])
            missing_v = target_verbs - len(raw["verbs"])
            missing_a = target_adjectives - len(raw.get("adjectives", []))
            if missing_n <= 0 and missing_v <= 0 and missing_a <= 0:
                break
            req_n = min(max(missing_n, 1), _MAX_NOUNS_PER_REQUEST)
            req_v = min(max(missing_v, 1), _MAX_VERBS_PER_REQUEST)
            req_a = min(max(missing_a, 1), _MAX_ADJECTIVES_PER_REQUEST)
            print(
                "  Top-up "
                f"{round_idx}/3: requesting {req_n} nouns, {req_v} verbs, {req_a} adjectives "
                f"(missing {max(missing_n, 0)} / {max(missing_v, 0)} / {max(missing_a, 0)})..."
            )
            batch = _request_vocab_json(_build_prompt(req_n, req_v, req_a))

            for noun in _collect_items(batch, "nouns"):
                key = str(noun.get("english", "")).strip().lower()
                if key and key not in seen_nouns and len(raw["nouns"]) < target_nouns:
                    seen_nouns.add(key)
                    raw["nouns"].append(noun)
                elif key:
                    repeat_hits.add(key)

            for verb in _collect_items(batch, "verbs"):
                key = str(verb.get("english", "")).strip().lower()
                if key and key not in seen_verbs and len(raw["verbs"]) < target_verbs:
                    seen_verbs.add(key)
                    raw["verbs"].append(verb)
                elif key:
                    repeat_hits.add(key)

            for adj in _collect_items(batch, "adjectives"):
                key = str(adj.get("english", "")).strip().lower()
                if key and key not in seen_adjectives and len(raw["adjectives"]) < target_adjectives:
                    seen_adjectives.add(key)
                    raw["adjectives"].append(adj)
                elif key:
                    repeat_hits.add(key)

        if (
            len(raw["nouns"]) < target_nouns
            or len(raw["verbs"]) < target_verbs
            or len(raw.get("adjectives", [])) < target_adjectives
        ):
            if save:
                out_dir.mkdir(parents=True, exist_ok=True)
                partial_out_path.write_text(
                    json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                print(
                    f"Saved partial: {partial_out_path}  "
                    f"({len(raw['nouns'])} nouns, {len(raw['verbs'])} verbs, {len(raw.get('adjectives', []))} adjectives)"
                )
            raise ValueError(
                "LLM could not generate enough unique items for the requested size. "
                f"Requested {target_nouns} nouns/{target_verbs} verbs/{target_adjectives} adjectives, got "
                f"{len(raw['nouns'])}/{len(raw['verbs'])}/{len(raw.get('adjectives', []))}. "
                f"Partial output saved to: {partial_out_path}. "
                "Try smaller counts or run again."
            )

        raw["nouns"] = raw["nouns"][:target_nouns]
        raw["verbs"] = raw["verbs"][:target_verbs]
        raw["adjectives"] = raw["adjectives"][:target_adjectives]

    for group in ("nouns", "verbs", "adjectives", "others"):
        for item in raw.get(group, []):
            if isinstance(item, dict):
                for k, v in item.items():
                    if isinstance(v, str):
                        item[k] = v.strip()

    errors = validate_vocab_schema(raw, get_language_config(language))
    if errors:
        raise ValueError(
            f"LLM-generated vocab for '{theme}' failed schema validation:\n"
            + "\n".join(f"  • {e}" for e in errors)
        )

    if save:
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(
            f"Saved: {out_path}  "
            f"({len(raw['nouns'])} nouns, {len(raw['verbs'])} verbs, {len(raw.get('adjectives', []))} adjectives)"
        )

    return raw


def extend_vocab(
    theme: str,
    add_nouns: Optional[int] = None,
    add_verbs: Optional[int] = None,
    add_adjectives: Optional[int] = None,
    total_count: Optional[int] = None,
    level: str = "beginner",
    output_dir: Optional[Path] = None,
    language: str = "eng-jap",
) -> dict:
    """Extend an existing vocab file by generating and merging new items.

    New items are generated via LLM and merged by case-insensitive English key,
    preserving existing items and appending only unique additions.
    """
    out_dir = Path(output_dir) if output_dir else VOCAB_DIR
    out_path = out_dir / f"{theme}.json"
    if not out_path.exists():
        raise ValueError(
            f"Cannot extend missing theme '{theme}'. "
            f"Create it first or run 'jlesson vocab create "
            f"{theme} --nouns 12 --verbs 10'."
        )

    existing = json.loads(out_path.read_text(encoding="utf-8"))
    target_key = "hungarian" if language == "hun-eng" else "japanese"

    existing_english_words: list[str] = []
    existing_target_words: list[str] = []
    for group in ("nouns", "verbs", "adjectives", "others"):
        items = existing.get(group, [])
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            eng = str(item.get("english", "")).strip()
            tgt = str(item.get(target_key, "")).strip()
            if eng:
                existing_english_words.append(eng)
            if tgt:
                existing_target_words.append(tgt)

    generated = generate_vocab(
        theme=theme,
        num_nouns=add_nouns,
        num_verbs=add_verbs,
        num_adjectives=add_adjectives,
        total_count=total_count,
        level=level,
        save=False,
        avoid_english_words=existing_english_words,
        avoid_target_words=existing_target_words,
        output_dir=output_dir,
        language=language,
    )

    existing_nouns = existing.get("nouns", []) if isinstance(existing.get("nouns", []), list) else []
    existing_verbs = existing.get("verbs", []) if isinstance(existing.get("verbs", []), list) else []
    existing_adjectives = existing.get("adjectives", []) if isinstance(existing.get("adjectives", []), list) else []
    existing_others = existing.get("others", []) if isinstance(existing.get("others", []), list) else []

    merged_nouns, added_nouns = _merge_unique_by_english(existing_nouns, generated.get("nouns", []))
    merged_verbs, added_verbs = _merge_unique_by_english(existing_verbs, generated.get("verbs", []))
    merged_adjectives, added_adjectives = _merge_unique_by_english(
        existing_adjectives,
        generated.get("adjectives", []),
    )
    merged_others, added_others = _merge_unique_by_english(
        existing_others,
        generated.get("others", []),
    )

    merged = {
        **existing,
        "theme": existing.get("theme", theme),
        "nouns": merged_nouns,
        "verbs": merged_verbs,
        "adjectives": merged_adjectives,
        "others": merged_others,
    }

    errors = validate_vocab_schema(merged, get_language_config(language))
    if errors:
        raise ValueError(
            f"Merged vocab for '{theme}' failed schema validation:\n"
            + "\n".join(f"  • {e}" for e in errors)
        )

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"Extended: {out_path}  "
        f"(+{added_nouns} nouns, +{added_verbs} verbs, +{added_adjectives} adjectives, +{added_others} others, "
        f"totals: {len(merged_nouns)} nouns, {len(merged_verbs)} verbs, {len(merged_adjectives)} adjectives, {len(merged_others)} others)"
    )

    return merged
