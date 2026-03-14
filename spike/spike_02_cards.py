"""
Spike 02: Test Pillow text card rendering with Japanese fonts.

Generates sample video cards to verify:
- Japanese text rendering (kanji + kana)
- English text rendering
- Layout and visual design at 1080p
- System fonts (Yu Gothic) work correctly
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# --- Card dimensions (1080p) ---
WIDTH, HEIGHT = 1920, 1080
BG_COLOR = "#1a1a2e"
ACCENT_COLOR = "#4fc3f7"
TEXT_COLOR = "#ffffff"
DIM_COLOR = "#888888"
LABEL_COLOR = "#e0e0e0"

# --- Font paths (Windows system fonts) ---
# Yu Gothic Bold for Japanese, regular Segoe UI for English
JP_FONT_PATH = "C:/Windows/Fonts/YuGothB.ttc"
EN_FONT_PATH = "C:/Windows/Fonts/segoeui.ttf"
EN_BOLD_FONT_PATH = "C:/Windows/Fonts/segoeuib.ttf"

# Fallback to MS Gothic if Yu Gothic not found
if not Path(JP_FONT_PATH).exists():
    JP_FONT_PATH = "C:/Windows/Fonts/msgothic.ttc"


def load_fonts():
    """Load fonts at various sizes."""
    return {
        "jp_large": ImageFont.truetype(JP_FONT_PATH, 120),
        "jp_medium": ImageFont.truetype(JP_FONT_PATH, 64),
        "en_large": ImageFont.truetype(EN_BOLD_FONT_PATH, 56),
        "en_medium": ImageFont.truetype(EN_FONT_PATH, 40),
        "en_small": ImageFont.truetype(EN_FONT_PATH, 28),
        "label": ImageFont.truetype(EN_BOLD_FONT_PATH, 24),
    }


def draw_progress_bar(draw: ImageDraw.Draw, y: int, progress: float, total_width: int = 800):
    """Draw a progress bar centered horizontally."""
    bar_height = 6
    x_start = (WIDTH - total_width) // 2
    x_end = x_start + total_width
    filled_end = x_start + int(total_width * progress)

    # Background bar
    draw.rounded_rectangle(
        [x_start, y, x_end, y + bar_height],
        radius=3, fill="#333333"
    )
    # Filled bar
    if progress > 0:
        draw.rounded_rectangle(
            [x_start, y, filled_end, y + bar_height],
            radius=3, fill=ACCENT_COLOR
        )


def render_introduce_card(fonts: dict, progress: float = 0.1) -> Image.Image:
    """Render an [INTRODUCE] card: English → Japanese."""
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    cx = WIDTH // 2

    # Step label
    draw.text((cx, 60), "[INTRODUCE]  1/30", font=fonts["label"], anchor="mm", fill=DIM_COLOR)

    # English word (prompt)
    draw.text((cx, 300), "water", font=fonts["en_large"], anchor="mm", fill=ACCENT_COLOR)

    # Divider
    draw.line([(cx - 200, 400), (cx + 200, 400)], fill="#333333", width=2)

    # Japanese (reveal)
    draw.text((cx, 520), "水", font=fonts["jp_large"], anchor="mm", fill=TEXT_COLOR)

    # Kana + romaji annotation
    draw.text((cx, 640), "みず  ·  mizu", font=fonts["en_medium"], anchor="mm", fill=DIM_COLOR)

    # Progress bar
    draw_progress_bar(draw, HEIGHT - 80, progress)

    return img


def render_recall_card(fonts: dict, progress: float = 0.2) -> Image.Image:
    """Render a [RECALL] card: Japanese → English."""
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    cx = WIDTH // 2

    # Step label
    draw.text((cx, 60), "[RECALL]  2/30", font=fonts["label"], anchor="mm", fill=DIM_COLOR)

    # Japanese (prompt)
    draw.text((cx, 320), "魚", font=fonts["jp_large"], anchor="mm", fill=TEXT_COLOR)
    draw.text((cx, 440), "さかな  ·  sakana", font=fonts["en_medium"], anchor="mm", fill=DIM_COLOR)

    # Divider
    draw.line([(cx - 200, 520), (cx + 200, 520)], fill="#333333", width=2)

    # English (reveal)
    draw.text((cx, 620), "fish", font=fonts["en_large"], anchor="mm", fill=ACCENT_COLOR)

    # Progress bar
    draw_progress_bar(draw, HEIGHT - 80, progress)

    return img


def render_grammar_card(fonts: dict, progress: float = 0.8) -> Image.Image:
    """Render a [TRANSLATE] grammar card."""
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    cx = WIDTH // 2

    # Step label
    draw.text((cx, 60), "[TRANSLATE]  65/87", font=fonts["label"], anchor="mm", fill=DIM_COLOR)

    # Grammar context
    draw.text((cx, 160), "I / present / affirmative", font=fonts["en_small"], anchor="mm", fill="#666666")

    # English sentence (prompt)
    draw.text((cx, 300), "I drink water.", font=fonts["en_large"], anchor="mm", fill=ACCENT_COLOR)

    # Divider
    draw.line([(cx - 300, 400), (cx + 300, 400)], fill="#333333", width=2)

    # Japanese sentence (reveal)
    draw.text((cx, 520), "私は水を飲みます。", font=fonts["jp_medium"], anchor="mm", fill=TEXT_COLOR)

    # Romaji
    draw.text((cx, 620), "watashi wa mizu o nomimasu.", font=fonts["en_medium"], anchor="mm", fill=DIM_COLOR)

    # Progress bar
    draw_progress_bar(draw, HEIGHT - 80, progress)

    return img


def main():
    print("=== Spike 02: Pillow card rendering ===\n")

    fonts = load_fonts()
    print(f"Japanese font: {JP_FONT_PATH}")
    print(f"English font:  {EN_FONT_PATH}\n")

    cards = [
        ("card_introduce.png", render_introduce_card(fonts, 0.03)),
        ("card_recall.png", render_recall_card(fonts, 0.07)),
        ("card_grammar.png", render_grammar_card(fonts, 0.75)),
    ]

    for name, img in cards:
        path = OUTPUT_DIR / name
        img.save(path)
        print(f"  ✓ {path.name} ({img.size[0]}x{img.size[1]})")

    print(f"\nAll cards in: {OUTPUT_DIR.resolve()}")
    print("Open them to check visual quality!")


if __name__ == "__main__":
    main()
