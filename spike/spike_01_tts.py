"""
Spike 01: Test edge-tts with Japanese and English voices.

Generates audio files to verify:
- Japanese neural voice quality (NanamiNeural)
- English neural voice quality (AriaNeural)
- Speech rate control for learner-friendly pacing
"""

import asyncio
from pathlib import Path

import edge_tts

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


async def generate_audio(text: str, voice: str, filename: str, rate: str = "+0%"):
    """Generate a single audio file with edge-tts."""
    out_path = OUTPUT_DIR / filename
    tts = edge_tts.Communicate(text, voice=voice, rate=rate)
    await tts.save(str(out_path))
    print(f"  ✓ {out_path.name} ({voice}, rate={rate})")
    return out_path


async def main():
    print("=== Spike 01: edge-tts ===\n")

    # --- Japanese voice ---
    print("Japanese (ja-JP-NanamiNeural):")
    await generate_audio(
        "水を飲みます", "ja-JP-NanamiNeural", "jp_normal.mp3"
    )
    await generate_audio(
        "水を飲みます", "ja-JP-NanamiNeural", "jp_slow.mp3", rate="-30%"
    )
    await generate_audio(
        "私は水を飲みました", "ja-JP-NanamiNeural", "jp_sentence.mp3", rate="-20%"
    )

    # --- Japanese male voice ---
    print("\nJapanese male (ja-JP-KeitaNeural):")
    await generate_audio(
        "水を飲みます", "ja-JP-KeitaNeural", "jp_male.mp3"
    )

    # --- English voice ---
    print("\nEnglish (en-US-AriaNeural):")
    await generate_audio(
        "water", "en-US-AriaNeural", "en_water.mp3"
    )
    await generate_audio(
        "I drink water", "en-US-AriaNeural", "en_sentence.mp3"
    )

    # --- Subtitle / timing test ---
    print("\nSubtitle timing test:")
    out_path = OUTPUT_DIR / "jp_with_subs.mp3"
    sub_path = OUTPUT_DIR / "jp_with_subs.srt"
    tts = edge_tts.Communicate(
        "私は魚を食べます", voice="ja-JP-NanamiNeural", rate="-20%"
    )
    submaker = edge_tts.SubMaker()
    with open(out_path, "wb") as f:
        async for chunk in tts.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            else:
                submaker.feed(chunk)
    sub_path.write_text(submaker.get_srt(), encoding="utf-8")
    print(f"  ✓ {out_path.name} + {sub_path.name}")

    print(f"\nAll files in: {OUTPUT_DIR.resolve()}")
    print("Play them to check audio quality!")


if __name__ == "__main__":
    asyncio.run(main())
