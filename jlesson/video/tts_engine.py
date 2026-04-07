"""
TTS Engine Module

Extracted from spike_01_tts.py for production use.
Generates audio files for Japanese lesson items using edge-tts.
"""

import asyncio
from pathlib import Path
from typing import Optional

import edge_tts


class TTSEngine:
    """Text-to-speech engine using Microsoft Edge TTS."""

    def __init__(self, voice: str = "ja-JP-NanamiNeural", rate: str = "-20%"):
        """
        Initialize TTS engine.

        Args:
            voice: TTS voice name (default: Japanese female)
            rate: Speech rate adjustment (default: 20% slower)
        """
        self.voice = voice
        self.rate = rate

    async def generate_audio(
        self,
        text: str,
        output_path: Path,
        subtitle_path: Optional[Path] = None
    ) -> None:
        """
        Generate audio file from text.

        Args:
            text: Text to convert to speech
            output_path: Path for audio output (.mp3)
            subtitle_path: Optional path for subtitle file (.srt)
        """
        communicate = edge_tts.Communicate(text, voice=self.voice, rate=self.rate)

        if subtitle_path:
            # Generate audio with subtitles
            submaker = edge_tts.SubMaker()
            with open(output_path, "wb") as audio_file:
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        audio_file.write(chunk["data"])
                    else:
                        submaker.feed(chunk)

            # Write subtitle file
            subtitle_path.write_text(submaker.get_srt(), encoding="utf-8")
        else:
            # Simple audio generation
            await communicate.save(str(output_path))

    async def generate_batch(
        self,
        text_items: list[str],
        output_dir: Path,
        base_filename: str = "audio"
    ) -> list[Path]:
        """
        Generate audio files for multiple text items.

        Args:
            text_items: List of text strings to convert
            output_dir: Directory to save audio files
            base_filename: Base name for files (will be numbered)

        Returns:
            List of generated audio file paths
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        audio_paths = []

        for i, text in enumerate(text_items, 1):
            filename = f"{base_filename}_{i:02d}.mp3"
            audio_path = output_dir / filename
            await self.generate_audio(text, audio_path)
            audio_paths.append(audio_path)

        return audio_paths


# Pre-configured voice options
VOICES = {
    "japanese_female": "ja-JP-NanamiNeural",
    "japanese_male": "ja-JP-KeitaNeural",
    "english_female": "en-US-AriaNeural",
    "english_male": "en-US-GuyNeural",
    "english_uk_male": "en-GB-RyanNeural",
    "english_uk_female": "en-GB-SoniaNeural",
    "hungarian_female": "hu-HU-NoemiNeural",
    "hungarian_male": "hu-HU-TamasNeural",
    "german_female": "de-DE-KatjaNeural",
    "german_male": "de-DE-ConradNeural",
    "french_female": "fr-FR-DeniseNeural",
    "french_male": "fr-FR-HenriNeural",
}


def create_engine(voice_key: str = "japanese_female", rate: str = "-20%") -> TTSEngine:
    """
    Create a TTS engine with pre-configured voice.

    Args:
        voice_key: Either a key from VOICES dict (e.g. "japanese_female") or a
                   raw Edge-TTS voice name (e.g. "hu-HU-NoemiNeural").
        rate: Speech rate adjustment

    Returns:
        Configured TTSEngine instance
    """
    # Accept both a symbolic key and a raw voice name.
    voice = VOICES.get(voice_key, voice_key)
    return TTSEngine(voice=voice, rate=rate)