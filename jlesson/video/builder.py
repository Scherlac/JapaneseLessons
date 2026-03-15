"""
Video Builder Module

Extracted from spike_03_video.py and spike_04_full_pipeline.py for production use.
Assembles video clips from card images and audio using moviepy.
"""

from pathlib import Path
from typing import List, Optional, Tuple

from moviepy import (
    AudioFileClip,
    ColorClip,
    CompositeVideoClip,
    ImageClip,
    concatenate_videoclips,
)


class VideoBuilder:
    """Builds videos from card images and audio clips."""

    def __init__(self, fps: int = 30):
        """
        Initialize video builder.

        Args:
            fps: Frames per second for output video
        """
        self.fps = fps

    def create_clip(
        self,
        card_path: Path,
        audio_path: Optional[Path] = None,
        duration: Optional[float] = None,
        pause_before: float = 1.5,
        pause_after: float = 1.0
    ) -> CompositeVideoClip:
        """
        Create a video clip from a card image and optional audio.

        Args:
            card_path: Path to card image (.png)
            audio_path: Path to audio file (.mp3), optional
            duration: Clip duration in seconds, auto-calculated if None
            pause_before: Pause before audio starts
            pause_after: Pause after audio ends

        Returns:
            MoviePy CompositeVideoClip
        """
        # Load image clip
        img_clip = ImageClip(str(card_path))

        if audio_path and audio_path.exists():
            # Load audio
            audio_clip = AudioFileClip(str(audio_path))

            # Calculate timing
            audio_duration = audio_clip.duration
            total_duration = pause_before + audio_duration + pause_after

            # Set durations
            img_clip = img_clip.with_duration(total_duration)
            audio_clip = audio_clip.with_start(pause_before)

            # Attach audio directly — CompositeVideoClip only accepts video clips in moviepy 2.x
            return img_clip.with_audio(audio_clip)
        else:
            # Image only clip
            if duration is None:
                duration = 3.0  # Default duration for image-only clips
            return img_clip.with_duration(duration)

    def create_pause_clip(self, duration: float, color: str = "#000000") -> ColorClip:
        """
        Create a pause/black clip.

        Args:
            duration: Pause duration in seconds
            color: Background color

        Returns:
            MoviePy ColorClip
        """
        # moviepy 2.x ColorClip requires an RGB tuple, not a hex string.
        if isinstance(color, str):
            h = color.lstrip("#")
            color = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
        return ColorClip(size=(1920, 1080), color=color, duration=duration)

    def build_video(
        self,
        clips: List[CompositeVideoClip],
        output_path: Path,
        codec: str = "libx264",
        audio_codec: str = "aac",
        method: str = "ffmpeg"
    ) -> None:
        """
        Build and export final video from clips.

        Args:
            clips: List of video clips to concatenate
            output_path: Output video file path (.mp4)
            codec: Video codec
            audio_codec: Audio codec
            method: Composition method - "ffmpeg" (fast, default) or "moviepy" (compatible)
        """
        if not clips:
            raise ValueError("No clips provided")

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if method == "ffmpeg":
            # Try FFmpeg concat with copy (much faster, no quality loss)
            success = self._build_video_ffmpeg(clips, output_path, codec, audio_codec)
            if success:
                return

            print("FFmpeg method failed, falling back to MoviePy...")

        # Fallback to MoviePy (slower but more compatible)
        self._build_video_moviepy(clips, output_path, codec, audio_codec)

    def _build_video_ffmpeg(
        self,
        clips: List[CompositeVideoClip],
        output_path: Path,
        codec: str,
        audio_codec: str
    ) -> bool:
        """
        Build video using FFmpeg concat with stream copying.
        Returns True if successful, False if failed.
        """
        import subprocess
        import tempfile

        try:
            # Create temporary directory for intermediate files
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_dir_path = Path(temp_dir)
                temp_videos = []

                # Export each clip as intermediate video
                for i, clip in enumerate(clips):
                    temp_path = temp_dir_path / f"temp_clip_{i:03d}.mp4"
                    clip.write_videofile(
                        str(temp_path),
                        fps=self.fps,
                        codec=codec,
                        audio_codec=audio_codec,
                        logger=None  # Silent
                    )
                    temp_videos.append(temp_path)

                # Create concat list for FFmpeg
                concat_list = temp_dir_path / "concat_list.txt"
                with open(concat_list, 'w') as f:
                    for video in temp_videos:
                        f.write(f"file '{video}'\n")

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
                return result.returncode == 0

        except Exception as e:
            print(f"FFmpeg method error: {e}")
            return False

    def _build_video_moviepy(
        self,
        clips: List[CompositeVideoClip],
        output_path: Path,
        codec: str,
        audio_codec: str
    ) -> None:
        """
        Build video using MoviePy concatenation (slower but compatible).
        """
        final_clip = concatenate_videoclips(clips, method="compose")
        final_clip.write_videofile(
            str(output_path),
            fps=self.fps,
            codec=codec,
            audio_codec=audio_codec,
            logger='bar'
        )

    def build_from_items(
        self,
        items: List[dict],
        card_dir: Path,
        audio_dir: Path,
        output_path: Path,
        card_renderer: Optional['CardRenderer'] = None
    ) -> None:
        """
        Build video from lesson items with automatic card/audio generation.

        Args:
            items: List of lesson item dictionaries
            card_dir: Directory containing card images
            audio_dir: Directory containing audio files
            output_path: Output video path
            card_renderer: Optional CardRenderer for generating missing cards
        """
        clips = []

        for i, item in enumerate(items):
            # Determine file paths
            card_filename = f"card_{i+1:03d}.png"
            audio_filename = f"audio_{i+1:03d}.mp3"
            card_path = card_dir / card_filename
            audio_path = audio_dir / audio_filename

            # Generate card if missing and renderer provided
            if not card_path.exists() and card_renderer:
                # This would need item-specific rendering logic
                # For now, assume cards are pre-generated
                pass

            # Create clip
            clip = self.create_clip(card_path, audio_path)
            clips.append(clip)

        # Build final video
        self.build_video(clips, output_path)


# Convenience function
def create_video_builder(fps: int = 30) -> VideoBuilder:
    """Create a VideoBuilder with default settings."""
    return VideoBuilder(fps=fps)