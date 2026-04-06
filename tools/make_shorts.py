"""
make_shorts.py — Build 5 YouTube Shorts from blocks 1-5 of a lesson.

Each Short is one block: vocab nouns + verbs + grammar sentences assembled
into a 9:16 (1080×1920) vertical video, ≤60s target.

The existing 1920×1080 lesson cards are pillarboxed (blurred background crop)
into 1080×1920 frames using Pillow before assembly via moviepy.

USAGE
-----
    python tools/make_shorts.py
    python tools/make_shorts.py --blocks 1 2 3      # specific blocks
    python tools/make_shorts.py --lesson kiki        # different lesson (default: kiki)
    python tools/make_shorts.py --pause-card 1.2     # seconds per card pause after audio

OUTPUT
------
    output/kiki/eng-jap/ghibli - Kiki's Delivery Service/lesson_001/shorts/
        short_block_01.mp4
        short_block_02.mp4
        ...
        short_block_05.mp4

REQUIREMENTS
------------
    pip install moviepy Pillow
    conda install -c conda-forge ffmpeg
"""

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    from PIL import Image, ImageFilter
except ImportError:
    sys.exit("ERROR: Pillow not installed. Run: pip install Pillow")

try:
    from moviepy import AudioFileClip, ImageClip, concatenate_videoclips
    from moviepy import CompositeAudioClip
except ImportError:
    sys.exit("ERROR: moviepy not installed. Run: pip install moviepy")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SHORTS_W, SHORTS_H = 1080, 1920   # 9:16 vertical
CARD_W, CARD_H = 1920, 1080       # source card size

LESSON_ROOTS = {
    "kiki": Path(__file__).resolve().parent.parent
              / "output" / "kiki" / "eng-jap"
              / "ghibli - Kiki's Delivery Service" / "lesson_001",
    "totoro": Path(__file__).resolve().parent.parent
              / "output" / "totoro" / "eng-jap"
              / "my neighbor totoro" / "lesson_001",
    "ponyo": Path(__file__).resolve().parent.parent
              / "output" / "ponyo" / "eng-jap"
              / "ghibli - Ponyo" / "lesson_001",
}

PLANNER_JSON = "steps/canonical_planner/output.json"

# ---------------------------------------------------------------------------
# Block data — item ordering for each block (from output.json structure)
# nouns → verbs → adjectives → grammar (matches lesson card order)
# ---------------------------------------------------------------------------

def load_blocks(lesson_root: Path) -> list[dict]:
    """Load block definitions from canonical_planner output.json."""
    json_path = lesson_root / PLANNER_JSON
    if not json_path.exists():
        sys.exit(f"ERROR: Planner JSON not found: {json_path}")
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    return data[0]["blocks"]


def block_item_ids(block: dict) -> list[str]:
    """Return ordered item IDs for a block: nouns → verbs → adjectives → grammar."""
    seqs = block["content_sequences"]
    ids = []
    for section in ("nouns", "verbs", "adjectives", "grammar"):
        for item in seqs.get(section, []):
            ids.append(item["id"])
    return ids


# ---------------------------------------------------------------------------
# Card → 9:16 frame conversion
# ---------------------------------------------------------------------------

def make_vertical_frame(card_path: Path, tmp_dir: Path) -> Path:
    """
    Convert a 1920×1080 card to a 1080×1920 vertical frame.

    Strategy: blur + scale the source to fill 1080×1920 as background,
    then letterbox the original card centered on top.
    """
    out_path = tmp_dir / f"{card_path.stem}_v.png"
    if out_path.exists():
        return out_path

    img = Image.open(card_path).convert("RGB")

    # --- Background: scale card to fill 1080×1920, then blur ---
    bg_scale = max(SHORTS_W / CARD_W, SHORTS_H / CARD_H)
    bg_w = int(CARD_W * bg_scale)
    bg_h = int(CARD_H * bg_scale)
    bg = img.resize((bg_w, bg_h), Image.LANCZOS)
    # Center crop to 1080×1920
    left = (bg_w - SHORTS_W) // 2
    top = (bg_h - SHORTS_H) // 2
    bg = bg.crop((left, top, left + SHORTS_W, top + SHORTS_H))
    bg = bg.filter(ImageFilter.GaussianBlur(radius=20))
    # Darken slightly so card stands out
    from PIL import ImageEnhance
    bg = ImageEnhance.Brightness(bg).enhance(0.4)

    # --- Foreground: scale original card to fit within 1080 wide ---
    fg_w = SHORTS_W
    fg_h = int(CARD_H * (fg_w / CARD_W))
    fg = img.resize((fg_w, fg_h), Image.LANCZOS)

    # Paste centered vertically
    fg_top = (SHORTS_H - fg_h) // 2
    frame = bg.copy()
    frame.paste(fg, (0, fg_top))

    frame.save(out_path)
    return out_path


# ---------------------------------------------------------------------------
# Short builder
# ---------------------------------------------------------------------------

def build_short(
    block: dict,
    lesson_root: Path,
    output_path: Path,
    tmp_dir: Path,
    pause_after: float = 1.0,
    pause_before: float = 0.5,
    fps: int = 30,
) -> None:
    cards_dir = lesson_root / "cards"
    audio_dir = lesson_root / "audio"

    item_ids = block_item_ids(block)
    block_idx = block["block_index"]
    narrative = block["narrative"]["narrative"]

    print(f"\n  Block {block_idx}: {narrative[:60]}...")
    print(f"  Items: {len(item_ids)}")

    clips = []

    for item_id in item_ids:
        card_path = cards_dir / f"{item_id}_card_en_ja.png"
        if not card_path.exists():
            print(f"    SKIP (no card): {item_id}")
            continue

        # Convert to vertical frame
        v_frame = make_vertical_frame(card_path, tmp_dir)

        # Find audio — prefer EN+JP pair, fall back to EN only
        audio_en = audio_dir / f"{item_id}_audio_en.mp3"
        audio_ja = audio_dir / f"{item_id}_audio_ja_f.mp3"

        valid_audio = [p for p in [audio_en, audio_ja] if p.exists()]

        if valid_audio:
            # Position audio tracks sequentially
            positioned = []
            t = pause_before
            for ap in valid_audio:
                ac = AudioFileClip(str(ap))
                positioned.append(ac.with_start(t))
                t += ac.duration + 0.3  # 0.3s gap between EN and JP

            total_dur = t - 0.3 + pause_after
            img_clip = ImageClip(str(v_frame)).with_duration(total_dur)

            if len(positioned) == 1:
                clip = img_clip.with_audio(positioned[0])
            else:
                combined = CompositeAudioClip(positioned)
                clip = img_clip.with_audio(combined)
        else:
            print(f"    WARN (no audio): {item_id}")
            clip = ImageClip(str(v_frame)).with_duration(2.5)

        clips.append(clip)

    if not clips:
        print(f"  ERROR: No clips generated for block {block_idx}")
        return

    total_est = sum(c.duration for c in clips)
    print(f"  Estimated duration: {total_est:.1f}s ({len(clips)} cards)")
    if total_est > 60:
        print(f"  WARNING: Exceeds 60s YouTube Shorts limit — consider reducing items")

    # Concatenate and export
    output_path.parent.mkdir(parents=True, exist_ok=True)
    final = concatenate_videoclips(clips, method="compose")
    print(f"  Rendering → {output_path.name}")
    final.write_videofile(
        str(output_path),
        fps=fps,
        codec="libx264",
        audio_codec="aac",
        logger=None,
    )
    print(f"  Saved: {output_path} ({output_path.stat().st_size / (1024*1024):.1f} MB)")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Build YouTube Shorts from lesson blocks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--lesson", default="kiki",
        choices=list(LESSON_ROOTS),
        help="Lesson to process (default: kiki)",
    )
    parser.add_argument(
        "--blocks", nargs="+", type=int, default=[1, 2, 3, 4, 5],
        metavar="N",
        help="Block indices to render (default: 1 2 3 4 5)",
    )
    parser.add_argument(
        "--pause-card", type=float, default=1.0, dest="pause_after",
        help="Pause after audio on each card in seconds (default: 1.0)",
    )
    parser.add_argument(
        "--fps", type=int, default=30,
        help="Output FPS (default: 30)",
    )
    args = parser.parse_args()

    lesson_root = LESSON_ROOTS[args.lesson]
    if not lesson_root.exists():
        sys.exit(f"ERROR: Lesson folder not found: {lesson_root}")

    blocks = load_blocks(lesson_root)
    block_map = {b["block_index"]: b for b in blocks}

    shorts_dir = lesson_root / "shorts"
    shorts_dir.mkdir(exist_ok=True)

    print(f"Lesson:   {args.lesson}")
    print(f"Blocks:   {args.blocks}")
    print(f"Output:   {shorts_dir}")

    with tempfile.TemporaryDirectory(prefix="jlesson_shorts_") as tmp:
        tmp_dir = Path(tmp)
        for block_idx in args.blocks:
            if block_idx not in block_map:
                print(f"\nWARN: Block {block_idx} not found, skipping")
                continue
            out = shorts_dir / f"short_block_{block_idx:02d}.mp4"
            build_short(
                block=block_map[block_idx],
                lesson_root=lesson_root,
                output_path=out,
                tmp_dir=tmp_dir,
                pause_after=args.pause_after,
                fps=args.fps,
            )

    print(f"\nDone. {len(args.blocks)} shorts in: {shorts_dir}")


if __name__ == "__main__":
    main()
