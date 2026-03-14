#!/usr/bin/env python3
"""
Japanese Lesson Generator CLI

Generates structured LLM prompts for Japanese learning lessons.
Uses vocabulary JSON files and configurable grammar dimensions.

Usage:
    python generate_lesson.py --theme food
    python generate_lesson.py --theme travel --nouns 6 --verbs 6
    python generate_lesson.py --theme food --output lesson_food.md
    python generate_lesson.py --list-themes
"""

import argparse
import json
import random
import sys
from pathlib import Path

from lesson_generator import generate_lesson_items, render_lesson_markdown
from prompt_template import (
    DIMENSIONS_BEGINNER,
    GRAMMAR_PATTERNS_BEGINNER,
    PERSONS_BEGINNER,
    build_lesson_prompt,
    build_vocab_prompt,
)

VOCAB_DIR = Path(__file__).parent / "vocab"


def _resolve_grammar_pairs(
    vocab: dict, nouns: list[dict], verbs: list[dict], n: int = 3,
) -> list[tuple[dict, dict]] | None:
    """Resolve explicit grammar_pairs from vocab, or return None for auto-pairing."""
    if "grammar_pairs" not in vocab:
        return None
    noun_by_en = {item["english"]: item for item in nouns}
    verb_by_en = {item["english"]: item for item in verbs}
    pairs = []
    for pair in vocab["grammar_pairs"]:
        verb = verb_by_en.get(pair["verb"])
        noun = noun_by_en.get(pair["noun"])
        if verb and noun:
            pairs.append((verb, noun))
    return pairs[:n] if pairs else None


# ---------------------------------------------------------------------------
# Vocabulary loading
# ---------------------------------------------------------------------------

def list_themes() -> list[str]:
    """Return available theme names from vocab/ directory."""
    return sorted(p.stem for p in VOCAB_DIR.glob("*.json"))


def load_vocab(theme: str) -> dict:
    """Load a vocabulary file by theme name."""
    path = VOCAB_DIR / f"{theme}.json"
    if not path.exists():
        available = ", ".join(list_themes()) or "(none)"
        print(f"Error: theme '{theme}' not found. Available: {available}", file=sys.stderr)
        sys.exit(1)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def pick_items(items: list[dict], count: int, shuffle: bool = True) -> list[dict]:
    """Select `count` items from list. Shuffles by default for variety."""
    if count >= len(items):
        return list(items)
    pool = list(items)
    if shuffle:
        random.shuffle(pool)
    return pool[:count]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a Japanese lesson prompt for an LLM.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
examples:
  python generate_lesson.py --theme food
  python generate_lesson.py --theme travel --nouns 4 --verbs 4
  python generate_lesson.py --theme food -o lesson_food.md
  python generate_lesson.py --list-themes
  python generate_lesson.py --generate-vocab shopping
  python generate_lesson.py --generate-vocab school --nouns 15 --verbs 12
        """,
    )

    parser.add_argument(
        "--theme", "-t",
        help="Vocabulary theme (must match a file in vocab/).",
    )
    parser.add_argument(
        "--list-themes",
        action="store_true",
        help="List available vocabulary themes and exit.",
    )
    parser.add_argument(
        "--nouns", "-n",
        type=int, default=6,
        help="Number of nouns to include (default: 6).",
    )
    parser.add_argument(
        "--verbs", "-v",
        type=int, default=6,
        help="Number of verbs to include (default: 6).",
    )
    parser.add_argument(
        "--seed", "-s",
        type=int, default=None,
        help="Random seed for reproducible vocab selection.",
    )
    parser.add_argument(
        "--no-shuffle",
        action="store_true",
        help="Pick first N items instead of shuffling.",
    )
    parser.add_argument(
        "--output", "-o",
        type=str, default=None,
        help="Write prompt to file instead of stdout.",
    )
    parser.add_argument(
        "--generate-vocab",
        type=str, default=None,
        metavar="THEME",
        help="Generate an LLM prompt to create vocabulary for a new theme.",
    )
    parser.add_argument(
        "--level",
        type=str, default="beginner",
        choices=["beginner", "intermediate", "advanced"],
        help="Difficulty level for vocab generation (default: beginner).",
    )
    parser.add_argument(
        "--create",
        action="store_true",
        help="Generate a complete lesson (JSON + Markdown) instead of an LLM prompt.",
    )

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    # --list-themes
    if args.list_themes:
        themes = list_themes()
        if themes:
            print("Available themes:")
            for t in themes:
                print(f"  - {t}")
        else:
            print(f"No themes found. Add JSON files to: {VOCAB_DIR}")
        return

    # --generate-vocab
    if args.generate_vocab:
        prompt = build_vocab_prompt(
            theme=args.generate_vocab,
            num_nouns=args.nouns if args.nouns != 6 else 12,
            num_verbs=args.verbs if args.verbs != 6 else 10,
            level=args.level,
        )
        if args.output:
            out_path = Path(args.output)
            out_path.write_text(prompt, encoding="utf-8")
            print(f"Vocab prompt written to: {out_path}", file=sys.stderr)
        else:
            print(prompt)
        return

    # --create: generate a complete lesson (JSON + Markdown)
    if args.create:
        if not args.theme:
            parser.error("--theme is required with --create")

        if args.seed is not None:
            random.seed(args.seed)

        vocab = load_vocab(args.theme)
        nouns = pick_items(vocab["nouns"], args.nouns, shuffle=not args.no_shuffle)
        verbs = pick_items(vocab["verbs"], args.verbs, shuffle=not args.no_shuffle)

        # Resolve grammar pairs: explicit from vocab or auto-paired
        grammar_pairs = _resolve_grammar_pairs(vocab, nouns, verbs)

        items = generate_lesson_items(nouns, verbs, grammar_pairs=grammar_pairs)

        # Save JSON
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)

        lesson_data = {
            "theme": args.theme,
            "total_items": len(items),
            "items": items,
        }
        json_path = output_dir / f"lesson_{args.theme}.json"
        json_path.write_text(
            json.dumps(lesson_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        # Save Markdown
        md_path = output_dir / f"lesson_{args.theme}.md"
        md_content = render_lesson_markdown(items, args.theme)
        md_path.write_text(md_content, encoding="utf-8")

        # Summary
        phase_counts: dict[str, int] = {}
        for item in items:
            phase_counts[item["phase"]] = phase_counts.get(item["phase"], 0) + 1

        summary = " + ".join(f"{c} {p}" for p, c in phase_counts.items())
        print(f"Created lesson: {args.theme}")
        print(f"  Items:  {len(items)} ({summary})")
        print(f"  JSON:   {json_path}")
        print(f"  Review: {md_path}")
        return

    # --theme is required for lesson generation
    if not args.theme:
        parser.error("--theme is required (or use --list-themes / --generate-vocab)")

    # Seed
    if args.seed is not None:
        random.seed(args.seed)

    # Load and select vocabulary
    vocab = load_vocab(args.theme)
    nouns = pick_items(vocab["nouns"], args.nouns, shuffle=not args.no_shuffle)
    verbs = pick_items(vocab["verbs"], args.verbs, shuffle=not args.no_shuffle)

    # Build prompt
    prompt = build_lesson_prompt(
        theme=args.theme,
        nouns=nouns,
        verbs=verbs,
        persons=PERSONS_BEGINNER,
        grammar_patterns=GRAMMAR_PATTERNS_BEGINNER,
        dimensions=DIMENSIONS_BEGINNER,
    )

    # Output
    if args.output:
        out_path = Path(args.output)
        out_path.write_text(prompt, encoding="utf-8")
        print(f"Prompt written to: {out_path}", file=sys.stderr)
    else:
        print(prompt)


if __name__ == "__main__":
    main()
