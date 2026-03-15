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

from curriculum import (
    load_curriculum,
    save_curriculum,
    suggest_new_vocab,
    summary as curriculum_summary,
)
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

    # Use all available nouns/verbs for lookup, not just selected ones
    all_nouns = vocab.get("nouns", [])
    all_verbs = vocab.get("verbs", [])

    noun_by_en = {item["english"]: item for item in all_nouns}
    verb_by_en = {item["english"]: item for item in all_verbs}

    pairs = []
    for pair in vocab["grammar_pairs"]:
        verb = verb_by_en.get(pair["verb"])
        noun = noun_by_en.get(pair["noun"])
        if verb and noun:
            # Only include if both verb and noun are in the selected lists
            if verb in verbs and noun in nouns:
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
        "--create-vocab",
        type=str, default=None,
        metavar="THEME",
        help="Generate vocabulary for a theme using the LLM and save to vocab/<theme>.json.",
    )
    parser.add_argument(
        "--show-curriculum",
        action="store_true",
        help="Display the current curriculum progress and exit.",
    )
    parser.add_argument(
        "--curriculum-path",
        type=str, default=None,
        metavar="FILE",
        help="Path to curriculum JSON file (default: curriculum/curriculum.json).",
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
    parser.add_argument(
        "--llm",
        action="store_true",
        help="Use LLM for enhanced natural grammar sentences (requires LLM setup).",
    )
    parser.add_argument(
        "--render-video",
        action="store_true",
        help="Render video from lesson items (requires --create and video dependencies).",
    )
    parser.add_argument(
        "--video-method",
        type=str, default="ffmpeg",
        choices=["ffmpeg", "moviepy"],
        help="Video composition method: ffmpeg (fast, default) or moviepy (compatible).",
    )

    return parser


def _render_video_from_lesson(lesson_data: dict, output_dir: Path, video_method: str = "ffmpeg") -> None:
    """Render video from lesson data using the video pipeline."""
    try:
        from tts_engine import create_engine
        from video_cards import CardRenderer
        from video_builder import VideoBuilder
    except ImportError as e:
        print(f"  Error: Video dependencies not available: {e}", file=sys.stderr)
        print("  Install with: pip install -e .[all] && conda install -c conda-forge ffmpeg", file=sys.stderr)
        return

    import asyncio

    items = lesson_data["items"]
    theme = lesson_data["theme"]

    # Create output directories
    cards_dir = output_dir / "cards"
    audio_dir = output_dir / "audio"
    cards_dir.mkdir(exist_ok=True)
    audio_dir.mkdir(exist_ok=True)

    # Initialize components
    tts_engine = create_engine("japanese_female", rate="-20%")
    card_renderer = CardRenderer()
    video_builder = VideoBuilder()

    async def render_video_async():
        # Generate audio for all items
        print("    Generating audio...")
        audio_paths = []
        for i, item in enumerate(items):
            text = item.get("tts_text", item.get("text", ""))
            voice_key = "japanese_female"  # Default
            if "tts_voice" in item:
                if "Nanami" in item["tts_voice"]:
                    voice_key = "japanese_female"
                elif "Keita" in item["tts_voice"]:
                    voice_key = "japanese_male"
                elif "Aria" in item["tts_voice"]:
                    voice_key = "english_female"

            # Create voice-specific engine for this item
            item_engine = create_engine(voice_key, rate="-20%")

            audio_filename = f"audio_{i+1:03d}.mp3"
            audio_path = audio_dir / audio_filename
            
            # Retry TTS generation up to 3 times with increasing delay
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    await item_engine.generate_audio(text, audio_path)
                    break
                except Exception as e:
                    if attempt < max_retries - 1:
                        print(f"      TTS failed (attempt {attempt+1}/{max_retries}): {e}")
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    else:
                        print(f"      TTS failed after {max_retries} attempts: {e}")
                        raise
            
            audio_paths.append(audio_path)
            
            # Add delay to avoid overwhelming TTS service
            await asyncio.sleep(1.0)

        # Generate cards for all items
        print("    Generating cards...")
        total_items = len(items)
        for i, item in enumerate(items):
            progress = (i + 1) / total_items

            # Determine card type based on step
            step = item["step"]
            if step == "INTRODUCE":
                # English → Japanese
                card = card_renderer.render_introduce_card(
                    english=item["prompt"],
                    japanese=item["reveal"],
                    kana="",  # Could extract from annotation
                    romaji="",  # Could extract from annotation
                    step_label=item["counter"],
                    progress=progress
                )
            elif step == "RECALL":
                # Japanese → English
                card = card_renderer.render_recall_card(
                    japanese=item["prompt"],
                    kana="",  # Could extract from annotation
                    romaji="",  # Could extract from annotation
                    english=item["reveal"],
                    step_label=item["counter"],
                    progress=progress
                )
            else:
                # TRANSLATE or other grammar steps
                card = card_renderer.render_translate_card(
                    english=item["prompt"],
                    japanese=item["reveal"],
                    romaji="",  # Could extract from annotation
                    context=f"{item['phase']} / {step.lower()}",
                    step_label=item["counter"],
                    progress=progress
                )

            # Save card
            card_path = cards_dir / "03d"
            card_renderer.save_card(card, card_path)

        # Build video
        print("    Building video...")
        video_path = output_dir / f"lesson_{theme}.mp4"

        # Create clips for each item
        clips = []
        for i, item in enumerate(items):
            card_path = cards_dir / "03d"
            audio_path = audio_dir / "03d"
            clip = video_builder.create_clip(card_path, audio_path)
            clips.append(clip)

        # Build final video
        video_builder.build_video(clips, video_path, method=video_method)
        print(f"  Video:  {video_path}")

    # Run async video rendering
    asyncio.run(render_video_async())


DEFAULT_CURRICULUM_PATH = Path(__file__).parent / "curriculum" / "curriculum.json"


def _get_curriculum_path(args) -> Path:
    return Path(args.curriculum_path) if args.curriculum_path else DEFAULT_CURRICULUM_PATH


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    # --show-curriculum
    if args.show_curriculum:
        cur = load_curriculum(_get_curriculum_path(args))
        print(curriculum_summary(cur))
        return

    # --create-vocab
    if args.create_vocab:
        from vocab_generator import generate_vocab
        generate_vocab(
            theme=args.create_vocab,
            num_nouns=args.nouns if args.nouns != 6 else 12,
            num_verbs=args.verbs if args.verbs != 6 else 10,
            level=args.level,
        )
        return

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

        items = generate_lesson_items(nouns, verbs, grammar_pairs=grammar_pairs, use_llm=args.llm)

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

        # Render video if requested
        if args.render_video:
            print("  Rendering video...")
            _render_video_from_lesson(lesson_data, output_dir, args.video_method)

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
