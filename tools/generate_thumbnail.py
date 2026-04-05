"""Generate a Gumroad thumbnail for the Totoro Japanese lesson using OpenAI image models."""

import argparse
import base64
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


STYLES = {
    "dark-minimal": (
        "Minimalist digital product thumbnail, clean flat illustration style. "
        "Muted sage green, charcoal, and warm cream tones. "
        "Dark forest green gradient background. "
        "Style: Swiss poster design, Gumroad product cover aesthetic."
    ),
    "watercolor-kids": (
        "Warm, dreamy watercolor illustration in the style of a Japanese animated film background painting. "
        "Soft pastel palette: sky blue, moss green, warm ochre, blush pink, and cream. "
        "Light cream background with delicate watercolor wash texture and gentle gradients. "
        "Whimsical, serene, nostalgic — evoking the hand-painted feel of classic anime film art. "
        "Style: Studio Ghibli background art aesthetic, lush hand-painted watercolor."
    ),
}

CONTENTS = {
    "totoro": (
        "A giant friendly round forest creature with pointy ears standing under a large "
        "camphor tree. The creature holds a small umbrella high above its head, "
        "well above its tall pointy ears, sheltering itself from the rain. "
        "Two small happy girls stand beside it, one younger looking up in wonder. "
        "Gentle rain falling. Lush green forest surroundings. "
        "No copyrighted character likenesses, no anime screenshots."
    ),
    "totoro-sky": (
        "Two small girls ride joyfully on the back of a giant round forest creature with pointy ears "
        "as it soars silently above the Japanese countryside at golden hour. "
        "Below, patchwork rice fields, a winding river, and a small rural village glow in warm amber light. "
        "Soft white cumulus clouds drift around them; the sky fades from deep blue above to warm orange at the horizon. "
        "The characters are small against the vast glowing sky, evoking wonder and freedom. "
        "No copyrighted character likenesses, no anime screenshots."
    ),
    "cat-bus": (
        "A giant fluffy cat-shaped bus with twelve furry legs runs joyfully along a winding country road at night. "
        "It has large bright round glowing eyes like headlights, a wide grinning mouth, and soft cream-coloured fur. "
        "The windows are warm amber-lit silhouettes of happy passengers inside. "
        "Tall grass sways in its wake, fireflies glow in the dark meadow around it, "
        "and a starry indigo sky stretches above rolling forested hills. "
        "No copyrighted character likenesses, no anime screenshots."
    ),
}

LAYOUT = (
    "The image has an infographic-poster layout with the main illustration centered. "
    "Left side: a vertical column of 5-6 small pastel color swatch circles (the palette used in the illustration). "
    "Top-right corner: a small circle that looks like the Japanese flag — a clean white circle with a solid red dot in its center. "
    "No text near the flag, no labels, just the flag icon. "
    "Bottom edge: a row of small rounded pill badges. Some contain only an emoji, others contain an emoji plus a short number or short text. "
    "Emoji-only pills should be narrower (nearly square), while pills with text should be wider to fit the content. "
    "These badges are subtle, elegant, flat design, part of the artwork — not overlaid. "
    "They use soft muted colors matching the illustration palette. "
    "Square 1:1 aspect ratio. No copyrighted character likenesses, no anime screenshots."
)

LAYOUT_COVER = (
    "Wide cinematic 16:9 composition in the style of a Studio Ghibli film still. "
    "The illustration fills the full frame with rich landscape depth: detailed foreground elements, "
    "warm-lit midground with the main characters, and a soft atmospheric background that stretches to the horizon. "
    "Top-right corner: a small circle that looks like the Japanese flag — a clean white circle with a solid red dot in its center. No text near it. "
    "No pill badges. No color swatches. No text elements other than the flag circle. "
    "Wide 16:9 landscape aspect ratio. No copyrighted character likenesses, no anime screenshots."
)

# Format definitions: format_name -> (api_size_landscape, output_size)
FORMATS = {
    "thumbnail":    {"api_landscape": False, "output_size": (600, 600)},
    "cover-small":  {"api_landscape": True,  "output_size": (1280, 720)},
    "cover-large":  {"api_landscape": True,  "output_size": (1920, 1080)},
}

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output" / "totoro" / "eng-jap" / "my neighbor totoro" / "lesson_001"


def build_prompt(style: str, content: str, level: str, content_type: str, lang: str, extra_tags: list[str], fmt: str = "thumbnail") -> str:
    style_text = STYLES.get(style)
    if not style_text:
        print(f"Error: Unknown style '{style}'. Available: {', '.join(STYLES)}", file=sys.stderr)
        sys.exit(1)
    content_text = CONTENTS.get(content)
    if not content_text:
        print(f"Error: Unknown content '{content}'. Available: {', '.join(CONTENTS)}", file=sys.stderr)
        sys.exit(1)

    # Map tags to emoji-only or emoji+number for prompt
    level_map = {"from-zero": "🌱", "beginner": "🌿", "n5": "📗", "n4": "📘"}
    type_map = {"narrative-video": "🎬", "flashcards": "🃏", "workbook": "📝"}

    level_label = level_map.get(level, "🌱")
    type_label = type_map.get(content_type, "📦")

    pills = [level_label, type_label]
    if extra_tags:
        for t in extra_tags:
            import re as _re
            num = _re.search(r'\d+', t)
            if "block" in t and num:
                pills.append(f"🧱 {num.group()}")
            elif "word" in t and num:
                pills.append(f"📖 {num.group()}")
            else:
                pills.append(f"✦ {t}")

    # Source language pill at the end
    src_lang = lang.split("-")[0].upper().replace("ENG", "EN").replace("JAP", "JP")
    pills.append(src_lang)

    tag_instructions = (
        f"The top-right circle is the Japanese flag (white circle, red center dot) — no text near it. "
        f"The bottom pill badges from left to right show: {', '.join(repr(p) for p in pills)}. "
        f"Emoji-only pills (like '{level_label}' and '{type_label}') are narrow, nearly square. "
        f"Pills with text (like numbers or 'EN') are wider. "
    )

    layout = LAYOUT_COVER if FORMATS.get(fmt, {}).get("api_landscape") else LAYOUT
    is_cover = FORMATS.get(fmt, {}).get("api_landscape", False)
    if is_cover:
        return f"{style_text} {content_text} {layout}"
    return f"{style_text} {content_text} {layout} {tag_instructions}"


MODELS = ["gpt-image-1.5", "gpt-image-1", "gpt-image-1-mini", "dall-e-3", "dall-e-2"]

# API generation sizes per model, keyed by landscape flag
MODEL_SIZES = {
    # (model, landscape) -> api size
    ("gpt-image-1.5",   False): "1024x1024",
    ("gpt-image-1.5",   True):  "1536x1024",
    ("gpt-image-1",     False): "1024x1024",
    ("gpt-image-1",     True):  "1536x1024",
    ("gpt-image-1-mini",False): "1024x1024",
    ("gpt-image-1-mini",True):  "1536x1024",
    ("dall-e-3",        False): "1024x1024",
    ("dall-e-3",        True):  "1792x1024",
    ("dall-e-2",        False): "1024x1024",
    ("dall-e-2",        True):  "1024x1024",  # dall-e-2 doesn't support wide
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a Gumroad thumbnail with OpenAI image models")
    parser.add_argument("--style", default="dark-minimal", choices=list(STYLES), help="Visual style preset")
    parser.add_argument("--content", default="totoro", choices=list(CONTENTS), help="Scene content preset")
    parser.add_argument("--model", default="gpt-image-1.5", choices=MODELS, help="OpenAI image model")
    parser.add_argument("--level", default="from-zero", help="Level tag (e.g. from-zero, beginner, n5)")
    parser.add_argument("--content-type", default="narrative-video", dest="content_type",
                        help="Content type tag (e.g. narrative-video, flashcards, workbook)")
    parser.add_argument("--lang", default="eng-jap", help="Language pair tag (e.g. eng-jap, eng-kor)")
    parser.add_argument("--tags", nargs="*", default=[], help="Extra custom tags (e.g. 30-blocks 120-words)")
    parser.add_argument("--no-tags", action="store_true", help="Skip tag overlay entirely")
    parser.add_argument("--format", default="thumbnail", choices=list(FORMATS),
                        help="Output format: thumbnail (600x600), cover-small (1280x720), cover-large (1920x1080)")
    parser.add_argument("--input-image", dest="input_image", help="Path to existing image (skip generation, just resize + apply tags)")
    args = parser.parse_args()


    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("LLM_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY or LLM_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    client = OpenAI(api_key=api_key)

    prompt = build_prompt(args.style, args.content, args.level, args.content_type, args.lang, args.tags, args.format)
    print(f"Generating {args.format} [model={args.model}, style={args.style}, content={args.content}]...")
    print(f"Prompt: {prompt[:100]}...")

    fmt_cfg = FORMATS[args.format]
    landscape = fmt_cfg["api_landscape"]
    output_size = fmt_cfg["output_size"]

    gen_kwargs = {
        "model": args.model,
        "prompt": prompt,
        "size": MODEL_SIZES[(args.model, landscape)],
        "n": 1,
    }
    if args.model.startswith("dall-e"):
        gen_kwargs["quality"] = "hd"
    else:
        # gpt-image models use low/medium/high
        gen_kwargs["quality"] = "high"

    response = client.images.generate(**gen_kwargs)

    # gpt-image-1 returns b64_json by default, dall-e models return url
    image_data = response.data[0]
    revised_prompt = getattr(image_data, "revised_prompt", None)
    if revised_prompt:
        print(f"\nRevised prompt: {revised_prompt}")

    import httpx

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = OUTPUT_DIR / f"{args.format}_{args.model}_{args.style}_{timestamp}.png"

    print(f"Downloading to {output_path}...")
    if image_data.b64_json:
        output_path.write_bytes(base64.b64decode(image_data.b64_json))
    elif image_data.url:
        resp = httpx.get(image_data.url, timeout=60)
        resp.raise_for_status()
        output_path.write_bytes(resp.content)

    # Resize to target output size
    img = Image.open(output_path)
    img = img.resize(output_size, Image.LANCZOS)

    img.save(output_path)
    w, h = output_size
    print(f"Saved (resized to {w}x{h}): {output_path}")
    print(f"Size: {output_path.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
