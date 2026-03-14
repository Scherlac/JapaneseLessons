"""
Spike 05: Performance test for video generation

Tests video composition performance with small dataset (2 cards, 2 audio files).
Compares moviepy composition vs ffmpeg stream copying.
"""

import time
from pathlib import Path

from moviepy import AudioFileClip, ImageClip, CompositeVideoClip, concatenate_videoclips
import subprocess

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


def time_moviepy_composition():
    """Test video composition using moviepy."""
    print("=== MoviePy Composition Test ===")

    # Use existing files
    card1_path = OUTPUT_DIR / "card_introduce.png"
    card2_path = OUTPUT_DIR / "card_recall.png"
    audio1_path = OUTPUT_DIR / "jp_normal.mp3"
    audio2_path = OUTPUT_DIR / "en_water.mp3"

    if not all(p.exists() for p in [card1_path, card2_path, audio1_path, audio2_path]):
        print("Missing required files. Run spike_01_tts.py and spike_02_cards.py first.")
        return

    start_time = time.time()

    # Create clips
    clips = []

    # First clip: Japanese
    img_clip1 = ImageClip(str(card1_path))
    audio_clip1 = AudioFileClip(str(audio1_path))
    audio_duration1 = audio_clip1.duration
    total_duration1 = 1.5 + audio_duration1 + 1.0  # pause_before + audio + pause_after

    img_clip1 = img_clip1.with_duration(total_duration1).with_audio(audio_clip1.with_start(1.5))

    clip1 = img_clip1
    clips.append(clip1)

    # Second clip: English
    img_clip2 = ImageClip(str(card2_path))
    audio_clip2 = AudioFileClip(str(audio2_path))
    audio_duration2 = audio_clip2.duration
    total_duration2 = 1.5 + audio_duration2 + 1.0

    img_clip2 = img_clip2.with_duration(total_duration2).with_audio(audio_clip2.with_start(1.5))

    clip2 = img_clip2
    clips.append(clip2)

    # Concatenate and export
    final_clip = concatenate_videoclips(clips, method="compose")
    output_path = OUTPUT_DIR / "performance_moviepy.mp4"

    final_clip.write_videofile(
        str(output_path),
        fps=30,
        codec="libx264",
        audio_codec="aac",
        logger='bar'
    )

    end_time = time.time()
    duration = end_time - start_time

    print(".2f")
    print(f"Output: {output_path}")

    return duration


def time_ffmpeg_copy():
    """Test video composition using ffmpeg stream copying."""
    print("\n=== FFmpeg Copy Test ===")

    # First, we need to create intermediate video files with moviepy (but minimal encoding)
    # Then use ffmpeg to concatenate them without re-encoding

    start_time = time.time()

    # Create individual video clips (minimal encoding)
    card1_path = OUTPUT_DIR / "card_introduce.png"
    card2_path = OUTPUT_DIR / "card_recall.png"
    audio1_path = OUTPUT_DIR / "jp_normal.mp3"
    audio2_path = OUTPUT_DIR / "en_water.mp3"

    if not all(p.exists() for p in [card1_path, card2_path, audio1_path, audio2_path]):
        print("Missing required files.")
        return

    # Create intermediate videos
    temp_videos = []

    for i, (card_path, audio_path) in enumerate([(card1_path, audio1_path), (card2_path, audio2_path)], 1):
        img_clip = ImageClip(str(card_path))
        audio_clip = AudioFileClip(str(audio_path))

        audio_duration = audio_clip.duration
        total_duration = 1.5 + audio_duration + 1.0

        img_clip = img_clip.with_duration(total_duration).with_audio(audio_clip.with_start(1.5))

        clip = img_clip

        temp_path = OUTPUT_DIR / f"temp_clip_{i}.mp4"
        clip.write_videofile(
            str(temp_path),
            fps=30,
            codec="libx264",
            audio_codec="aac",
            logger=None  # Silent
        )
        temp_videos.append(temp_path)

    # Now use ffmpeg to concatenate without re-encoding
    concat_list = OUTPUT_DIR / "concat_list.txt"
    with open(concat_list, 'w') as f:
        for video in temp_videos:
            f.write(f"file '{video}'\n")

    output_path = OUTPUT_DIR / "performance_ffmpeg.mp4"

    # FFmpeg concat with copy (no re-encoding)
    cmd = [
        "ffmpeg",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_list),
        "-c", "copy",  # Copy streams without re-encoding
        "-y",  # Overwrite
        str(output_path)
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        end_time = time.time()
        duration = end_time - start_time
        print(".2f")
        print(f"Output: {output_path}")
        return duration
    else:
        print(f"FFmpeg failed: {result.stderr}")
        return None


def analyze_performance():
    """Analyze and compare performance."""
    print("\n=== Performance Analysis ===")

    moviepy_time = time_moviepy_composition()
    ffmpeg_time = time_ffmpeg_copy()

    if moviepy_time and ffmpeg_time:
        print("\nComparison:")
        print(f"MoviePy time: {moviepy_time:.2f}s")
        print(f"FFmpeg time: {ffmpeg_time:.2f}s")

        if ffmpeg_time < moviepy_time:
            speedup = moviepy_time / ffmpeg_time
            print(f"FFmpeg is {speedup:.1f}x faster")
        else:
            slowdown = ffmpeg_time / moviepy_time
            print(f"FFmpeg is {slowdown:.1f}x slower")

    # Check file sizes
    moviepy_file = OUTPUT_DIR / "performance_moviepy.mp4"
    ffmpeg_file = OUTPUT_DIR / "performance_ffmpeg.mp4"

    if moviepy_file.exists():
        print(f"\nMoviePy file size: {moviepy_file.stat().st_size / 1024:.1f} KB")

    if ffmpeg_file.exists():
        print(f"FFmpeg file size: {ffmpeg_file.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    analyze_performance()