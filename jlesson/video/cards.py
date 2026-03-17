"""
Video Card Renderer Module

Extracted from spike_02_cards.py for production use.
Renders text cards for Japanese lesson videos using Pillow.
"""

from pathlib import Path
from typing import Dict, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont

from jlesson.language_config import LanguageConfig
from jlesson.lesson_pipeline import StepInfo
from jlesson.models import GeneralItem, Touch, TouchIntent


class CardRenderer:
    """Renders video cards for Japanese lessons."""

    def __init__(
        self,
        width: int = 1920,
        height: int = 1080,
        bg_color: str = "#1a1a2e",
        accent_color: str = "#4fc3f7",
        text_color: str = "#ffffff",
        dim_color: str = "#888888",
        label_color: str = "#e0e0e0",
        display_lang: Optional[str] = "en",
        source_lang: Optional[str] = "en",
        target_lang: Optional[str] = "jp",
    ):
        """
        Initialize card renderer.

        Args:
            width: Card width in pixels
            height: Card height in pixels
            bg_color: Background color
            accent_color: Accent color for highlights
            text_color: Primary text color
            dim_color: Secondary text color
            label_color: Label text color
            display_lang: Display language
            source_lang: Source language
            target_lang: Target language
        """
        self.width = width
        self.height = height
        self.bg_color = bg_color
        self.accent_color = accent_color
        self.text_color = text_color
        self.dim_color = dim_color
        self.label_color = label_color
        self.display_lang = display_lang
        self.source_lang = source_lang
        self.target_lang = target_lang

        self.fonts = self._load_fonts()

        self.source_fonts = {
            x[3:] :y 
            for x, y in self.fonts.items()
            if x.startswith(f"{self.source_lang}_")
        }

        self.target_fonts = {
            x[3:] :y 
            for x, y in self.fonts.items()
            if x.startswith(f"{self.target_lang}_")
        }

        self.intent_mapping = {
            TouchIntent.INTRODUCE: "Introduce",
            TouchIntent.RECALL: "Recall",
            TouchIntent.REINFORCE: "Reinforce",
            TouchIntent.CONFIRM: "Confirm",
            TouchIntent.LOCK_IN: "Lock-in",
            TouchIntent.TRANSLATE: "Translate",
            TouchIntent.COMPREHEND: "Comprehend",
            TouchIntent.UNKNOWN: "",
        }

    def _load_fonts(self) -> Dict[str, ImageFont.FreeTypeFont]:
        """Load system fonts for Japanese and English text."""
        # Font paths (Windows system fonts)
        jp_font_path = "C:/Windows/Fonts/YuGothB.ttc"
        en_font_path = "C:/Windows/Fonts/segoeui.ttf"
        en_bold_font_path = "C:/Windows/Fonts/segoeuib.ttf"

        # Fallback to MS Gothic if Yu Gothic not found
        if not Path(jp_font_path).exists():
            jp_font_path = "C:/Windows/Fonts/msgothic.ttc"

        return {
            "jp_large": ImageFont.truetype(jp_font_path, 120),
            "jp_medium": ImageFont.truetype(jp_font_path, 64),
            "en_large": ImageFont.truetype(en_bold_font_path, 56),
            "en_medium": ImageFont.truetype(en_font_path, 40),
            "en_small": ImageFont.truetype(en_font_path, 28),
            "label": ImageFont.truetype(en_bold_font_path, 24),
            # Hungarian-English cards — Segoe UI for both (Latin script)
            "hun_target_large": ImageFont.truetype(en_bold_font_path, 80),
            "hun_native_medium": ImageFont.truetype(en_font_path, 48),
            "hun_pron": ImageFont.truetype(en_font_path, 32),
        }

    def _draw_progress_bar(
        self,
        draw: ImageDraw.Draw,
        y: int,
        progress: float,
        total_width: int = 800
    ) -> None:
        """Draw a progress bar centered horizontally."""
        bar_height = 6
        x_start = (self.width - total_width) // 2
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
                radius=3, fill=self.accent_color
            )

    def render_card(
        self,
        item: GeneralItem,
        touch: Touch | None,
        step: StepInfo,
        lang_cfg: LanguageConfig | None =None,
    ) -> Image.Image:
        """
        Render a card based on the touch intent.

        Args:
            item: GeneralItem object containing card data
            touch: Touch object containing intent information
            step: StepInfo object containing step details
            step_label: Step counter (e.g., "1/30")
            progress: Progress bar fill (0.0 to 1.0)

        Returns:
            PIL Image object
        """
        img = Image.new("RGB", (self.width, self.height), self.bg_color)
        draw = ImageDraw.Draw(img)
        cx = self.width // 2

        intent = touch.intent if touch else TouchIntent.UNKNOWN
        intent_label = self.intent_mapping.get(intent, "")

        # Step label
        draw.text((cx, 60), f"{intent_label}  {step.label}", font=self.fonts["label"],
                 anchor="mm", fill=self.dim_color)

        if intent.show_source():
            # English word (prompt)
            draw.text((cx, 300), item.source.display_text, font=self.source_fonts["large"],
                    anchor="mm", fill=self.accent_color)

        # Divider
        draw.line([(cx - 200, 400), (cx + 200, 400)], fill="#333333", width=2)

        if intent.show_target():
            # Target  (reveal)
            draw.text((cx, 520), item.target.display_text, font=self.target_fonts["large"],
                    anchor="mm", fill=self.text_color)

            # Target pronunciation (reveal) + special
            if item.target.extra and len(item.target.extra) > 0:
                annotation = ""
                special = list(item.target.extra.values()) + [item.target.pronunciation]
                annotation = " / ".join(special)
            else:
                annotation = f"{item.target.pronunciation}"

            # FIXME size issue with long annotations 
            draw.text((cx, 640), annotation, font=self.target_fonts["medium"],
                    anchor="mm", fill=self.dim_color)

        # Progress bar
        self._draw_progress_bar(draw, self.height - 80, step.progress)

        return img

    def save_card(self, img: Image.Image, path: Path) -> None:
        """Save a rendered card image to disk.

        Ensures parent directories exist and writes PNG data.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        img.save(path, format="PNG")


# Convenience function
def create_renderer(**kwargs) -> CardRenderer:
    """Create a CardRenderer with custom settings."""
    return CardRenderer(**kwargs)

