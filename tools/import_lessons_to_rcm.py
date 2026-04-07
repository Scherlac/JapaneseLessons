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

from jlesson.models import GeneralItem, Phase
from jlesson.rcm import open_rcm

# Asset keys and the filename suffixes the asset_compiler produces per key.
# Pattern: {item_id}_{suffix}
_AUDIO_SUFFIXES: dict[str, str] = {
    "audio_src": "audio_en.mp3",        # source language audio (always English for eng-* pairs)
    "audio_tar_f": "audio_fr_f.mp3",    # target language female
    "audio_tar_m": "audio_fr_m.mp3",    # target language male
}
_CARD_SUFFIXES: dict[str, str] = {
    "card_src": "card_en.png",
    "card_tar": "card_fr.png",
    "card_src_tar": "card_en_fr.png",
}


def _derive_audio_suffix(language_code: str) -> dict[str, str]:
    """Derive audio filename suffixes from language code like 'eng-fre'."""
    parts = language_code.split("-")
    src = parts[0][:2] if parts else "en"
    tar = parts[1][:2] if len(parts) > 1 else "fr"
    return {
        "audio_src": f"audio_{src}.mp3",
        "audio_tar_f": f"audio_{tar}_f.mp3",
        "audio_tar_m": f"audio_{tar}_m.mp3",
    }


def _derive_card_suffix(language_code: str) -> dict[str, str]:
    parts = language_code.split("-")
    src = parts[0][:2] if parts else "en"
    tar = parts[1][:2] if len(parts) > 1 else "fr"
    return {
        "card_src": f"card_{src}.png",
        "card_tar": f"card_{tar}.png",
        "card_src_tar": f"card_{src}_{tar}.png",
    }


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
    audio_suffixes = _derive_audio_suffix(language_code)
    card_suffixes = _derive_card_suffix(language_code)
    all_suffixes = {**audio_suffixes, **card_suffixes}

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
            for block in blocks:
                lesson_items.extend(_items_from_block(block))

            for item in lesson_items:
                canonical = item.canonical
                if not canonical.id:
                    continue

                # Check if branch already exists
                existing = store.get_branch(canonical.id, language_code)
                is_new = existing is None

                store.upsert_item(canonical)
                store.upsert_branch(canonical.id, language_code, item)

                # Register existing compiled assets
                for asset_key, suffix in all_suffixes.items():
                    # Audio assets
                    if "audio" in asset_key:
                        candidate = audio_dir / f"{canonical.id}_{suffix}"
                    else:
                        candidate = cards_dir / f"{canonical.id}_{suffix}"
                    if candidate.exists():
                        store.register_asset(canonical.id, language_code, asset_key, candidate)
                        total_assets += 1

                total_items += 1
                if is_new:
                    total_new += 1

            if lesson_id and lesson_items:
                store.record_lesson_items(lesson_id, theme, language_code, lesson_items)

        # Print stats
        stats = store.stats()
        print(f"\n{'='*50}")
        print(f"Import complete")
        print(f"  Items processed : {total_items}")
        print(f"  New to store    : {total_new}")
        print(f"  Assets found    : {total_assets}")
        print(f"  Store totals    : {stats['items']} items | {stats['branches']} branches | {stats['assets']} assets")

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
