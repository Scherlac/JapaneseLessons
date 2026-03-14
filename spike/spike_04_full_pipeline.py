"""
Spike 04: Full mini pipeline — end-to-end from vocab to video.

Runs the complete chain:
  vocab dict → card images → TTS audio → assembled video

This proves the full pipeline works without needing LLM output.
Uses 3 hardcoded lesson items (2 nouns + 1 grammar sentence).
"""

import asyncio
from pathlib import Path

import edge_tts
from PIL import Image, ImageDraw, ImageFont
from moviepy import AudioFileClip, ImageClip, concatenate_videoclips

OUTPUT_DIR = Path(__file__).parent / "output" / "mini_pipeline"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# --- Fonts ---
JP_FONT_PATH = "C:/Windows/Fonts/YuGothB.ttc"
EN_FONT_PATH = "C:/Windows/Fonts/segoeui.ttf"
EN_BOLD_PATH = "C:/Windows/Fonts/segoeuib.ttf"
if not Path(JP_FONT_PATH).exists():
    JP_FONT_PATH = "C:/Windows/Fonts/msgothic.ttc"

WIDTH, HEIGHT = 1920, 1080
BG_COLOR = "#1a1a2e"

# --- Lesson items (hardcoded for spike) ---
ITEMS = [
    {
        "step": "INTRODUCE",
        "counter": "1/6",
        "prompt": "water",
        "reveal": "水",
        "annotation": "みず · mizu",
        "tts_text": "みず",
        "tts_voice": "ja-JP-NanamiNeural",
    },
    {
        "step": "RECALL",
        "counter": "2/6",
        "prompt": "卵",
        "reveal": "egg",
        "annotation": "たまご · tamago",
        "tts_text": "たまご",
        "tts_voice": "ja-JP-NanamiNeural",
    },
    {
        "step": "TRANSLATE",
        "counter": "1/9",
        "prompt": "I drink water.",
        "reveal": "私は水を飲みます。",
        "annotation": "watashi wa mizu o nomimasu",
        "tts_text": "私は水を飲みます",
        "tts_voice": "ja-JP-NanamiNeural",
    },
]


def render_card(item: dict, index: int, total: int) -> Path:
    """Render a single lesson card and save as PNG."""
    fonts = {
        "label": ImageFont.truetype(EN_BOLD_PATH, 24),
        "prompt": ImageFont.truetype(EN_BOLD_PATH if item["step"] != "RECALL" else JP_FONT_PATH,
                                      80 if item["step"] != "TRANSLATE" else 56),
        "reveal": ImageFont.truetype(JP_FONT_PATH if item["step"] != "RECALL" else EN_BOLD_PATH,
                                      100 if item["step"] != "TRANSLATE" else 64),
        "annotation": ImageFont.truetype(EN_FONT_PATH, 36),
    }

    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)
    cx = WIDTH // 2

    # Label
    draw.text((cx, 60), f"[{item['step']}]  {item['counter']}", font=fonts["label"], anchor="mm", fill="#888888")

    # Prompt
    draw.text((cx, 300), item["prompt"], font=fonts["prompt"], anchor="mm", fill="#4fc3f7")

    # Divider
    draw.line([(cx - 250, 420), (cx + 250, 420)], fill="#333333", width=2)

    # Reveal
    draw.text((cx, 550), item["reveal"], font=fonts["reveal"], anchor="mm", fill="#ffffff")

    # Annotation
    draw.text((cx, 680), item["annotation"], font=fonts["annotation"], anchor="mm", fill="#888888")

    # Progress bar
    progress = (index + 1) / total
    bar_w = 800
    x0 = (WIDTH - bar_w) // 2
    draw.rounded_rectangle([x0, HEIGHT - 80, x0 + bar_w, HEIGHT - 74], radius=3, fill="#333333")
    draw.rounded_rectangle([x0, HEIGHT - 80, x0 + int(bar_w * progress), HEIGHT - 74], radius=3, fill="#4fc3f7")

    path = OUTPUT_DIR / f"card_{index:03d}.png"
    img.save(path)
    return path


async def generate_tts(item: dict, index: int) -> Path:
    """Generate TTS audio for one item."""
    path = OUTPUT_DIR / f"audio_{index:03d}.mp3"
    tts = edge_tts.Communicate(item["tts_text"], voice=item["tts_voice"], rate="-20%")
    await tts.save(str(path))
    return path


def assemble_video(cards: list[Path], audios: list[Path], out_path: Path):
    """Combine cards + audio into a single video."""
    clips = []
    for card, audio_path in zip(cards, audios):
        audio = AudioFileClip(str(audio_path))
        pause_before = 1.5
        pause_after = 1.5
        total = pause_before + audio.duration + pause_after

        img_clip = ImageClip(str(card), duration=total).resized((1920, 1080))
        audio_delayed = audio.with_start(pause_before)
        clips.append(img_clip.with_audio(audio_delayed))

    final = concatenate_videoclips(clips, method="compose")
    final.write_videofile(str(out_path), fps=24, codec="libx264", audio_codec="aac", logger="bar")
    return final.duration


async def main():
    print("=== Spike 04: Full mini pipeline ===\n")
    total = len(ITEMS)

    # Step 1: Render cards
    print("Step 1: Rendering cards...")
    cards = []
    for i, item in enumerate(ITEMS):
        path = render_card(item, i, total)
        cards.append(path)
        print(f"  ✓ {path.name}")

    # Step 2: Generate TTS
    print("\nStep 2: Generating TTS audio...")
    audios = []
    for i, item in enumerate(ITEMS):
        path = await generate_tts(item, i)
        audios.append(path)
        print(f"  ✓ {path.name}")

    # Step 3: Assemble video
    print("\nStep 3: Assembling video...")
    out_path = OUTPUT_DIR / "mini_lesson.mp4"
    duration = assemble_video(cards, audios, out_path)

    print(f"\n✓ Done! Video: {out_path.resolve()}")
    print(f"  Duration: {duration:.1f}s")
    print(f"  Items: {total}")
    print("  Play it to verify the full pipeline!")


if __name__ == "__main__":
    asyncio.run(main())
