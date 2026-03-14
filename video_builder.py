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

            # Combine
            return CompositeVideoClip([img_clip, audio_clip.with_start(pause_before)])
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
        return ColorClip(size=(1920, 1080), color=color, duration=duration)

    def build_video(
        self,
        clips: List[CompositeVideoClip],
        output_path: Path,
        codec: str = "libx264",
        audio_codec: str = "aac"
    ) -> None:
        """
        Build and export final video from clips.

        Args:
            clips: List of video clips to concatenate
            output_path: Output video file path (.mp4)
            codec: Video codec
            audio_codec: Audio codec
        """
        if not clips:
            raise ValueError("No clips provided")

        # Concatenate all clips
        final_clip = concatenate_videoclips(clips, method="compose")

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Export video
        final_clip.write_videofile(
            str(output_path),
            fps=self.fps,
            codec=codec,
            audio_codec=audio_codec,
            verbose=False,
            logger=None
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