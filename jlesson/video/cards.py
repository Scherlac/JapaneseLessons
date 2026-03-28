"""
Video Card Renderer Module

Extracted from spike_02_cards.py for production use.
Renders text cards for Japanese lesson videos using Pillow.
"""

from pathlib import Path
from typing import Dict, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont

from jlesson.language_config import LanguageConfig
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
            "jp_small": ImageFont.truetype(jp_font_path, 40),
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
        label: str = "",
        progress: float = 0.0,
        lang_cfg: LanguageConfig | None =None,
    ) -> Image.Image:
        """
        Render a reusable static card.

        Args:
            item: GeneralItem object containing card data
            touch: Optional Touch object containing intent information
            label: Optional top label for touch-specific rendering
            progress: Optional progress bar fill (0.0 to 1.0)

        Returns:
            PIL Image object
        """
        img = Image.new("RGB", (self.width, self.height), self.bg_color)
        draw = ImageDraw.Draw(img)
        cx = self.width // 2

        intent = touch.intent if touch else TouchIntent.UNKNOWN
        intent_label = self.intent_mapping.get(intent, "")

        header = "  ".join(part for part in (intent_label, label) if part)
        if header:
            draw.text((cx, 60), header, font=self.fonts["label"], anchor="mm", fill=self.dim_color)

        if intent.show_source():
            # English word (prompt)
            draw.text((cx, 300), item.source.display_text, font=self.source_fonts["large"],
                    anchor="mm", fill=self.accent_color)

        # Divider
        draw.line([(cx - 200, 400), (cx + 200, 400)], fill="#333333", width=2)

        if intent.show_target():
            extra_keys = (
                lang_cfg.target_extra_display_keys if lang_cfg else []
            )
            extra_font_keys = (
                lang_cfg.target_card_extra_font_keys if lang_cfg else {}
            )
            self._draw_target_block(
                draw, cx, 440, item,
                self.target_fonts, self.fonts,
                extra_font_keys, extra_keys,
                self.text_color, self.dim_color,
            )

        if progress > 0:
            self._draw_progress_bar(draw, self.height - 80, progress)

        return img

    @staticmethod
    def _draw_target_block(
        draw: ImageDraw.Draw,
        cx: int,
        y_top: int,
        item: GeneralItem,
        target_fonts: dict,
        all_fonts: dict,
        extra_font_keys: dict,
        extra_display_keys: list,
        text_color: str,
        dim_color: str,
        gap_after_main: int = 20,
        gap_after_line: int = 12,
    ) -> None:
        """Draw the target reveal block: display text, pronunciation, then extra fields.

        All elements are stacked vertically and sized dynamically using getbbox()
        so no text overflows into the progress bar.

        Parameters
        ----------
        extra_font_keys
            Per-extra-key font mapping ``{extra_key: font_key}``.
            ``font_key`` must be a key in ``all_fonts``.
            Unrecognised or absent keys fall back to ``"en_small"``.
        """

        def _draw_line(y: int, text: str, font, fill: str) -> int:
            """Draw *text* centred at *cx*, top-aligned to *y*. Returns new y."""
            if not text or font is None:
                return y
            bbox = font.getbbox(text)
            h = bbox[3] - bbox[1]
            draw.text((cx, y + h // 2), text, font=font, anchor="mm", fill=fill)
            return y + h

        y = y_top

        # 1. Main target display text (large)
        font_main = target_fonts.get("large")
        if font_main and item.target.display_text:
            y = _draw_line(y, item.target.display_text, font_main, text_color)
            y += gap_after_main

        # 2. Pronunciation / romaji
        font_pron = target_fonts.get("medium", font_main)
        if font_pron and item.target.pronunciation:
            y = _draw_line(y, item.target.pronunciation, font_pron, dim_color)
            y += gap_after_line

        # 3. Extra fields — each may have its own font
        _fallback = all_fonts.get("en_small")
        keys = extra_display_keys if extra_display_keys else list(item.target.extra.keys())
        for key in keys:
            val = item.target.extra.get(key) or ""
            if val:
                fk = extra_font_keys.get(key, "en_small")
                font_extra = all_fonts.get(fk, _fallback)
                y = _draw_line(y, str(val), font_extra, dim_color)
                y += gap_after_line

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

