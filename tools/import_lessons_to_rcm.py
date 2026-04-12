"""Import already-generated lessons into the RCM store.

Walks a source directory tree looking for
  steps/lesson_planner/output.json
files, deserialises each GeneralItem, and upserts it into the RCM store.
Also registers any compiled assets found in the sibling audio/ and cards/
directories.

Optionally reads a curriculum JSON file to populate lesson membership.

Usage
-----
    conda activate base
    python tools/import_lessons_to_rcm.py \\
        --source-dir output/northern_exposure \\
        --language    eng-fre \\
        --rcm-path    rcm/ \\
        [--curriculum output/northern_exposure/curriculum_french.json]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure the project root is on sys.path when run directly
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from jlesson.asset_compiler import build_asset_suffix_map
from jlesson.llm_cache import LlmCacheTrace
from jlesson.models import GeneralItem, Phase
from jlesson.rcm import open_rcm


def _load_lesson_id_map(curriculum_path: Path) -> dict[str, int]:
    """Return {theme_lower -> lesson_id} from a curriculum JSON file."""
    if not curriculum_path.exists():
        return {}
    with open(curriculum_path, encoding="utf-8") as f:
        data = json.load(f)
    result: dict[str, int] = {}
    for lesson in data.get("lessons", []):
        theme = lesson.get("theme", "").lower().strip()
        if theme:
            result[theme] = lesson["id"]
    return result


def _load_step_traces(step_dir: Path) -> list[LlmCacheTrace]:
    """Read llm_cache.json from a step directory and return typed trace objects."""
    cache_file = step_dir / "llm_cache.json"
    if not cache_file.exists():
        return []
    with open(cache_file, encoding="utf-8") as f:
        data = json.load(f)
    traces = []
    for raw in data.get("calls", []):
        traces.append(LlmCacheTrace(
            prompt_hash=raw["prompt_hash"],
            response_hash=raw["response_hash"],
            cache_key=raw.get("cache_key"),
            cache_hit=bool(raw.get("cache_hit", False)),
            prompt_file=raw.get("prompt_file"),
            response_file=raw.get("response_file"),
            effort=raw.get("effort"),
            call_index=raw.get("call_index", 0),
            step_name=raw.get("step_name"),
            step_index=raw.get("step_index"),
            prompt_tokens=raw.get("prompt_tokens", 0),
            completion_tokens=raw.get("completion_tokens", 0),
            total_tokens=raw.get("total_tokens", 0),
        ))
    return traces


def _import_llm_usage(
    store,
    steps_dir: Path,
    block_items: dict[int, list[GeneralItem]],
    language_code: str,
) -> tuple[int, int]:
    """Import LLM usage traces from all step directories.

    For `lesson_planner` traces the call_index maps directly to block_index,
    so each trace is linked to the items produced in that block via
    ``record_item_llm_usage``.  For all other steps only the token counts are
    recorded (no per-item links, because there's no reliable 1-to-1 mapping).

    Returns (records_added, records_linked).
    """
    records_added = 0
    records_linked = 0

    # lesson_planner: one call per block — link to items in that block
    planner_traces = _load_step_traces(steps_dir / "lesson_planner")
    for trace in planner_traces:
        items_for_block = block_items.get(trace.call_index, [])
        if items_for_block:
            store.record_item_llm_usage(trace, language_code, items_for_block)
            records_linked += 1
        else:
            store.record_llm_usage(trace)
        records_added += 1

    # All other steps: record token usage without item links
    other_steps = ["canonical_planner", "review_sentences", "narrative_generator"]
    for step_name in other_steps:
        for trace in _load_step_traces(steps_dir / step_name):
            store.record_llm_usage(trace)
            records_added += 1

    return records_added, records_linked


def _items_from_block(block: dict) -> list[GeneralItem]:
    """Flatten all phases from a lesson_planner output block into GeneralItems."""
    items: list[GeneralItem] = []
    content_sequences = block.get("content_sequences", {})
    for phase_items in content_sequences.values():
        for raw_item in phase_items:
            try:
                items.append(GeneralItem.model_validate(raw_item))
            except Exception as exc:
                print(f"  [warn] skipping malformed item: {exc}")
    return items


def run_import(
    source_dir: Path,
    language_code: str,
    rcm_path: Path,
    curriculum_path: Path | None,
) -> None:
    all_suffixes = build_asset_suffix_map(language_code)

    lesson_id_map: dict[str, int] = {}
    if curriculum_path:
        lesson_id_map = _load_lesson_id_map(curriculum_path)

    planner_outputs = sorted(source_dir.rglob("steps/lesson_planner/output.json"))
    if not planner_outputs:
        print(f"No lesson_planner output.json files found under {source_dir}")
        return

    print(f"Found {len(planner_outputs)} lesson(s) to import.")

    total_items = 0
    total_new = 0
    total_assets = 0

    with open_rcm(rcm_path) as store:
        for planner_json in planner_outputs:
            lesson_dir = planner_json.parent.parent.parent  # steps/../..
            audio_dir = lesson_dir / "audio"
            cards_dir = lesson_dir / "cards"

            # Derive theme from directory name (two levels up from lesson_NNN)
            theme = lesson_dir.parent.name.lower().strip()
            lesson_id = lesson_id_map.get(theme, 0)

            print(f"\n  Lesson: {theme!r} (id={lesson_id})")

            with open(planner_json, encoding="utf-8") as f:
                blocks = json.load(f)

            lesson_items: list[GeneralItem] = []
            block_items: dict[int, list[GeneralItem]] = {}
            for block in blocks:
                block_gi = _items_from_block(block)
                lesson_items.extend(block_gi)
                block_items[block["block_index"]] = block_gi

            for item in lesson_items:
                canonical = item.canonical
                if not canonical.id:
                    continue

                # Check if branch already exists
                existing = store.get_branch(canonical.id, language_code)
                is_new = existing is None

                store.upsert_item(canonical)
                store.upsert_branch(canonical.id, language_code, item)

                # Register existing compiled assets — copy into central store
                for asset_key, suffix in all_suffixes.items():
                    if "audio" in asset_key:
                        candidate = audio_dir / f"{canonical.id}_{suffix}"
                    else:
                        candidate = cards_dir / f"{canonical.id}_{suffix}"
                    if candidate.exists():
                        store.register_asset(
                            canonical.id, language_code, asset_key, candidate,
                            copy_to_store=True,
                        )
                        total_assets += 1

                total_items += 1
                if is_new:
                    total_new += 1

            if lesson_id and lesson_items:
                store.record_lesson_items(lesson_id, theme, language_code, lesson_items)

            steps_dir = lesson_dir / "steps"
            llm_added, llm_linked = _import_llm_usage(store, steps_dir, block_items, language_code)
            if llm_added:
                print(f"    LLM usage records : {llm_added} added ({llm_linked} linked to items)")

        # Print stats
        stats = store.stats()
        print(f"\n{'='*50}")
        print(f"Import complete")
        print(f"  Items processed : {total_items}")
        print(f"  New to store    : {total_new}")
        print(f"  Assets found    : {total_assets}")
        print(f"  Store totals    : {stats['items']} items | {stats['branches']} branches | {stats['assets']} assets")
        print(f"  LLM usage       : {stats['llm_usage_records']} records | {stats['llm_usage_links']} links | {stats['llm_total_tokens']} tokens")

        if stats["duplicate_texts"]:
            print(f"\nDuplicate words (same text, different IDs):")
            for dup in stats["duplicate_texts"]:
                print(f"  {dup['text']!r:40s}  ×{dup['count']}")
        else:
            print("\nNo duplicate words found.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Import generated lessons into the RCM store.")
    parser.add_argument("--source-dir", required=True, type=Path, help="Root directory to search for lesson output.")
    parser.add_argument("--language", required=True, help="Language code, e.g. eng-fre.")
    parser.add_argument("--rcm-path", required=True, type=Path, help="RCM root directory (rcm.db will be created here).")
    parser.add_argument("--curriculum", type=Path, default=None, help="Path to curriculum JSON for lesson ID mapping.")
    args = parser.parse_args()

    run_import(
        source_dir=args.source_dir,
        language_code=args.language,
        rcm_path=args.rcm_path,
        curriculum_path=args.curriculum,
    )


if __name__ == "__main__":
    main()
