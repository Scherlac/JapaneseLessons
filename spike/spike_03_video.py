"""
Spike 03: Test moviepy video assembly with image clips + audio.

Combines card images and TTS audio into a short video to verify:
- ImageClip from PNG works
- Audio attachment and sync
- Concatenation of multiple clips
- mp4 export via ffmpeg
"""

from pathlib import Path

from moviepy import (
    AudioFileClip,
    ColorClip,
    CompositeVideoClip,
    ImageClip,
    concatenate_videoclips,
)

OUTPUT_DIR = Path(__file__).parent / "output"

# Expected files from spike_01 and spike_02
AUDIO_FILES = {
    "en": OUTPUT_DIR / "en_water.mp3",
    "jp": OUTPUT_DIR / "jp_normal.mp3",
    "jp_sentence": OUTPUT_DIR / "jp_sentence.mp3",
}
CARD_FILES = {
    "introduce": OUTPUT_DIR / "card_introduce.png",
    "recall": OUTPUT_DIR / "card_recall.png",
    "grammar": OUTPUT_DIR / "card_grammar.png",
}


def check_prerequisites():
    """Verify that spike_01 and spike_02 outputs exist."""
    missing = []
    for label, path in {**AUDIO_FILES, **CARD_FILES}.items():
        if not path.exists():
            missing.append(f"  {label}: {path}")
    if missing:
        print("Missing files — run spike_01_tts.py and spike_02_cards.py first:")
        for m in missing:
            print(m)
        return False
    return True


def make_clip(card_path: Path, audio_path: Path, pause_before: float = 1.5, pause_after: float = 1.0):
    """
    Create a single video clip:
    - Show card image
    - Wait `pause_before` seconds (thinking time)
    - Play audio
    - Hold for `pause_after` seconds after audio ends
    """
    audio = AudioFileClip(str(audio_path))
    total_duration = pause_before + audio.duration + pause_after

    # Image fills entire duration
    card = ImageClip(str(card_path), duration=total_duration).resized((1920, 1080))

    # Offset audio to start after the pause
    audio_delayed = audio.with_start(pause_before)

    # Composite: card with delayed audio
    clip = card.with_audio(audio_delayed)
    return clip


def main():
    print("=== Spike 03: moviepy video assembly ===\n")

    if not check_prerequisites():
        return

    clips = []

    # Clip 1: INTRODUCE card + English audio
    print("  Building clip 1: INTRODUCE (en_water.mp3)...")
    clips.append(make_clip(CARD_FILES["introduce"], AUDIO_FILES["en"]))

    # Clip 2: INTRODUCE card + Japanese audio
    print("  Building clip 2: INTRODUCE (jp_normal.mp3)...")
    clips.append(make_clip(CARD_FILES["introduce"], AUDIO_FILES["jp"]))

    # Clip 3: RECALL card + Japanese audio
    print("  Building clip 3: RECALL (jp_normal.mp3)...")
    clips.append(make_clip(CARD_FILES["recall"], AUDIO_FILES["jp"]))

    # Clip 4: GRAMMAR card + Japanese sentence audio
    print("  Building clip 4: GRAMMAR (jp_sentence.mp3)...")
    clips.append(make_clip(CARD_FILES["grammar"], AUDIO_FILES["jp_sentence"]))

    # Concatenate all clips
    print("\n  Concatenating clips...")
    final = concatenate_videoclips(clips, method="compose")

    # Export
    out_path = OUTPUT_DIR / "spike_video.mp4"
    print(f"  Exporting to {out_path.name} ({final.duration:.1f}s)...")
    final.write_videofile(
        str(out_path),
        fps=24,
        codec="libx264",
        audio_codec="aac",
        logger="bar",
    )

    print(f"\n✓ Video saved: {out_path.resolve()}")
    print(f"  Duration: {final.duration:.1f}s")
    print("  Play it to check quality!")


if __name__ == "__main__":
    main()
