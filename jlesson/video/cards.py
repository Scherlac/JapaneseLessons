"""
Video Card Renderer Module

Extracted from spike_02_cards.py for production use.
Renders text cards for Japanese lesson videos using Pillow.
"""

from pathlib import Path
from typing import Dict, Optional

from PIL import Image, ImageDraw, ImageFont

from jlesson.language_config import LanguageConfig
from jlesson.models import GeneralItem, Touch, TouchIntent


class CardRenderer:
    """Renders video cards for Japanese lessons."""

    INTENT_LABELS = {
        TouchIntent.INTRODUCE: "Introduce",
        TouchIntent.RECALL: "Recall",
        TouchIntent.REINFORCE: "Reinforce",
        TouchIntent.CONFIRM: "Confirm",
        TouchIntent.LOCK_IN: "Lock-in",
        TouchIntent.TRANSLATE: "Translate",
        TouchIntent.COMPREHEND: "Comprehend",
        TouchIntent.UNKNOWN: "",
    }

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

        src_tag = f"{self.source_lang}_"
        self.source_fonts = {k[len(src_tag):]: v for k, v in self.fonts.items() if k.startswith(src_tag)}
        tgt_tag = f"{self.target_lang}_"
        self.target_fonts = {k[len(tgt_tag):]: v for k, v in self.fonts.items() if k.startswith(tgt_tag)}

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
            "jp_small": ImageFont.truetype(jp_font_path, 32),
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
        draw: ImageDraw.ImageDraw,
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

    @staticmethod
    def _measure_text_width(text: str, font: ImageFont.FreeTypeFont) -> float:
        """Return the rendered width of a single line of text."""
        if not text:
            return 0.0
        if hasattr(font, "getlength"):
            return float(font.getlength(text))
        bbox = font.getbbox(text)
        return float(bbox[2] - bbox[0])

    def _split_token_to_fit(
        self,
        token: str,
        font: ImageFont.FreeTypeFont,
        max_width: int,
    ) -> list[str]:
        """Split one long token into width-constrained chunks."""
        if not token:
            return [""]

        chunks: list[str] = []
        current = ""
        for char in token:
            candidate = f"{current}{char}"
            if current and self._measure_text_width(candidate, font) > max_width:
                chunks.append(current)
                current = char
            else:
                current = candidate

        if current:
            chunks.append(current)
        return chunks or [token]

    def _greedy_wrap(
        self,
        pieces: list[str],
        font: ImageFont.FreeTypeFont,
        max_width: int,
        sep: str = " ",
    ) -> list[str]:
        """Pack *pieces* into lines that fit within *max_width*, joining with *sep*."""
        lines: list[str] = []
        current = ""
        for piece in pieces:
            candidate = piece if not current else f"{current}{sep}{piece}"
            if current and self._measure_text_width(candidate, font) > max_width:
                lines.append(current)
                current = piece
            else:
                current = candidate
        if current:
            lines.append(current)
        return lines

    def _wrap_text_to_width(
        self,
        text: str,
        font: ImageFont.FreeTypeFont,
        max_width: int,
    ) -> str:
        """Insert newlines so text fits within *max_width* pixels."""
        if not text or max_width <= 0:
            return text

        wrapped: list[str] = []
        for paragraph in str(text).splitlines() or [str(text)]:
            if not paragraph or self._measure_text_width(paragraph, font) <= max_width:
                wrapped.append(paragraph)
            elif any(c.isspace() for c in paragraph):
                pieces: list[str] = []
                for word in paragraph.split():
                    if self._measure_text_width(word, font) > max_width:
                        pieces.extend(self._split_token_to_fit(word, font, max_width))
                    else:
                        pieces.append(word)
                wrapped.extend(self._greedy_wrap(pieces, font, max_width))
            else:
                wrapped.extend(self._split_token_to_fit(paragraph, font, max_width))

        return "\n".join(wrapped)

    def _draw_text_block(
        self,
        draw: ImageDraw.ImageDraw,
        cx: int,
        y_top: int,
        text: str,
        font: ImageFont.FreeTypeFont,
        fill: str,
        max_width: int,
        spacing: int | None = None,
    ) -> int:
        """Draw a centered multiline text block and return its bottom y."""
        if not text:
            return y_top

        if spacing is None:
            spacing_px = float(max(8, getattr(font, "size", 40) // 5))
        else:
            spacing_px = float(spacing)

        wrapped = self._wrap_text_to_width(text, font, max_width)
        bbox = draw.multiline_textbbox(
            (0, 0),
            wrapped,
            font=font,
            spacing=spacing_px,
            align="center",
        )
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        x = int(cx - (width / 2) - bbox[0])
        y = int(y_top - bbox[1])
        draw.multiline_text(
            (x, y),
            wrapped,
            font=font,
            fill=fill,
            spacing=spacing_px,
            align="center",
        )
        return int(y_top + height)

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
        intent_label = self.INTENT_LABELS.get(intent, "")

        header = "  ".join(part for part in (intent_label, label) if part)
        if header:
            draw.text((cx, 60), header, font=self.fonts["label"], anchor="mm", fill=self.dim_color)

        divider_y = 400
        if intent.show_source():
            source_bottom = self._draw_text_block(
                draw,
                cx,
                220,
                item.source.display_text,
                self.source_fonts["large"],
                self.accent_color,
                max_width=self.width - 420,
            )
            divider_y = max(divider_y, source_bottom + 50)

        # Divider
        draw.line([(cx - 200, divider_y), (cx + 200, divider_y)], fill="#333333", width=2)

        if intent.show_target():
            self._draw_target_block(draw, cx, divider_y + 40, item, lang_cfg)

        if progress > 0:
            self._draw_progress_bar(draw, self.height - 80, progress)

        return img

    def _draw_target_block(
        self,
        draw: ImageDraw.ImageDraw,
        cx: int,
        y_top: int,
        item: GeneralItem,
        lang_cfg: LanguageConfig | None = None,
    ) -> None:
        """Draw the target reveal block: display text, pronunciation, then extras."""
        y = y_top
        max_width = self.width - 320

        font_main = self.target_fonts.get("large")
        if font_main and item.target.display_text:
            y = self._draw_text_block(
                draw, cx, y, item.target.display_text, font_main, self.text_color, max_width
            )
            y += 20

        font_pron = self.target_fonts.get("medium", font_main)
        if font_pron and item.target.pronunciation:
            y = self._draw_text_block(
                draw, cx, y, item.target.pronunciation, font_pron, self.dim_color, max_width
            )
            y += 12

        extra_keys = lang_cfg.target_extra_display_keys if lang_cfg else list(item.target.extra.keys())
        extra_font_keys = lang_cfg.target_card_extra_font_keys if lang_cfg else {}
        fallback = self.fonts.get("en_small")
        for key in extra_keys:
            val = item.target.extra.get(key) or ""
            if val:
                fk = extra_font_keys.get(key, "en_small")
                font_extra = self.fonts.get(fk, fallback)
                if font_extra is None:
                    continue
                y = self._draw_text_block(
                    draw, cx, y, str(val), font_extra, self.dim_color, max_width
                )
                y += 12

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

