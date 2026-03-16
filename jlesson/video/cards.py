"""
Video Card Renderer Module

Extracted from spike_02_cards.py for production use.
Renders text cards for Japanese lesson videos using Pillow.
"""

from pathlib import Path
from typing import Dict, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont


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
        label_color: str = "#e0e0e0"
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
        """
        self.width = width
        self.height = height
        self.bg_color = bg_color
        self.accent_color = accent_color
        self.text_color = text_color
        self.dim_color = dim_color
        self.label_color = label_color

        self.fonts = self._load_fonts()

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

    def render_introduce_card(
        self,
        english: str,
        japanese: str,
        kana: str,
        romaji: str,
        step_label: str,
        progress: float = 0.0
    ) -> Image.Image:
        """
        Render an [INTRODUCE] card: English → Japanese reveal.

        Args:
            english: English word/text
            japanese: Japanese kanji
            kana: Japanese kana reading
            romaji: Romaji transcription
            step_label: Step counter (e.g., "1/30")
            progress: Progress bar fill (0.0 to 1.0)

        Returns:
            PIL Image object
        """
        img = Image.new("RGB", (self.width, self.height), self.bg_color)
        draw = ImageDraw.Draw(img)
        cx = self.width // 2

        # Step label
        draw.text((cx, 60), f"[INTRODUCE]  {step_label}", font=self.fonts["label"],
                 anchor="mm", fill=self.dim_color)

        # English word (prompt)
        draw.text((cx, 300), english, font=self.fonts["en_large"],
                 anchor="mm", fill=self.accent_color)

        # Divider
        draw.line([(cx - 200, 400), (cx + 200, 400)], fill="#333333", width=2)

        # Japanese (reveal)
        draw.text((cx, 520), japanese, font=self.fonts["jp_large"],
                 anchor="mm", fill=self.text_color)

        # Kana + romaji annotation
        annotation = f"{kana}  ·  {romaji}"
        draw.text((cx, 640), annotation, font=self.fonts["en_medium"],
                 anchor="mm", fill=self.dim_color)

        # Progress bar
        self._draw_progress_bar(draw, self.height - 80, progress)

        return img

    def render_recall_card(
        self,
        japanese: str,
        kana: str,
        romaji: str,
        english: str,
        step_label: str,
        progress: float = 0.0
    ) -> Image.Image:
        """
        Render a [RECALL] card: Japanese → English reveal.

        Args:
            japanese: Japanese kanji
            kana: Japanese kana reading
            romaji: Romaji transcription
            english: English word/text
            step_label: Step counter
            progress: Progress bar fill

        Returns:
            PIL Image object
        """
        img = Image.new("RGB", (self.width, self.height), self.bg_color)
        draw = ImageDraw.Draw(img)
        cx = self.width // 2

        # Step label
        draw.text((cx, 60), f"[RECALL]  {step_label}", font=self.fonts["label"],
                 anchor="mm", fill=self.dim_color)

        # Japanese (prompt)
        draw.text((cx, 320), japanese, font=self.fonts["jp_large"],
                 anchor="mm", fill=self.text_color)
        annotation = f"{kana}  ·  {romaji}"
        draw.text((cx, 440), annotation, font=self.fonts["en_medium"],
                 anchor="mm", fill=self.dim_color)

        # Divider
        draw.line([(cx - 200, 520), (cx + 200, 520)], fill="#333333", width=2)

        # English (reveal)
        draw.text((cx, 620), english, font=self.fonts["en_large"],
                 anchor="mm", fill=self.accent_color)

        # Progress bar
        self._draw_progress_bar(draw, self.height - 80, progress)

        return img

    def render_translate_card(
        self,
        english: str,
        japanese: str,
        romaji: str,
        context: str,
        step_label: str,
        progress: float = 0.0
    ) -> Image.Image:
        """
        Render a [TRANSLATE] grammar card.

        Args:
            english: English sentence
            japanese: Japanese sentence
            romaji: Romaji transcription
            context: Grammar context (e.g., "I / present / affirmative")
            step_label: Step counter
            progress: Progress bar fill

        Returns:
            PIL Image object
        """
        img = Image.new("RGB", (self.width, self.height), self.bg_color)
        draw = ImageDraw.Draw(img)
        cx = self.width // 2

        # Step label
        draw.text((cx, 60), f"[TRANSLATE]  {step_label}", font=self.fonts["label"],
                 anchor="mm", fill=self.dim_color)

        # Grammar context
        draw.text((cx, 160), context, font=self.fonts["en_small"],
                 anchor="mm", fill="#666666")

        # English sentence (prompt)
        draw.text((cx, 300), english, font=self.fonts["en_large"],
                 anchor="mm", fill=self.accent_color)

        # Divider
        draw.line([(cx - 300, 400), (cx + 300, 400)], fill="#333333", width=2)

        # Japanese sentence (reveal)
        draw.text((cx, 520), japanese, font=self.fonts["jp_medium"],
                 anchor="mm", fill=self.text_color)

        # Romaji
        draw.text((cx, 620), romaji, font=self.fonts["en_medium"],
                 anchor="mm", fill=self.dim_color)

        # Progress bar
        self._draw_progress_bar(draw, self.height - 80, progress)

        return img

    def save_card(self, card: Image.Image, output_path: Path) -> None:
        """
        Save a card image to file.

        Args:
            card: PIL Image object
            output_path: Output file path (.png)
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        card.save(output_path, "PNG")

    # ------------------------------------------------------------------
    # Touch-system card renderers
    # ------------------------------------------------------------------

    def render_en_card(
        self,
        english: str,
        label: str = "",
        progress: float = 0.0,
    ) -> Image.Image:
        """Render an English-only card (prompt side of en→jp touches)."""
        img = Image.new("RGB", (self.width, self.height), self.bg_color)
        draw = ImageDraw.Draw(img)
        cx = self.width // 2

        if label:
            draw.text(
                (cx, 60), label, font=self.fonts["label"],
                anchor="mm", fill=self.dim_color,
            )

        draw.text(
            (cx, self.height // 2 - 40), english,
            font=self.fonts["en_large"], anchor="mm", fill=self.accent_color,
        )

        self._draw_progress_bar(draw, self.height - 80, progress)
        return img

    def render_jp_card(
        self,
        japanese: str,
        kana: str = "",
        romaji: str = "",
        label: str = "",
        progress: float = 0.0,
    ) -> Image.Image:
        """Render a Japanese-only card (prompt side of jp→en / jp→jp touches)."""
        img = Image.new("RGB", (self.width, self.height), self.bg_color)
        draw = ImageDraw.Draw(img)
        cx = self.width // 2

        if label:
            draw.text(
                (cx, 60), label, font=self.fonts["label"],
                anchor="mm", fill=self.dim_color,
            )

        draw.text(
            (cx, self.height // 2 - 80), japanese,
            font=self.fonts["jp_large"], anchor="mm", fill=self.text_color,
        )

        parts = [p for p in (kana, romaji) if p]
        if parts:
            annotation = "  ·  ".join(parts)
            draw.text(
                (cx, self.height // 2 + 60), annotation,
                font=self.fonts["en_medium"], anchor="mm", fill=self.dim_color,
            )

        self._draw_progress_bar(draw, self.height - 80, progress)
        return img

    def render_bilingual_card(
        self,
        english: str,
        japanese: str,
        kana: str = "",
        romaji: str = "",
        label: str = "",
        progress: float = 0.0,
    ) -> Image.Image:
        """Render an EN+JP bilingual card (listen-first touches)."""
        img = Image.new("RGB", (self.width, self.height), self.bg_color)
        draw = ImageDraw.Draw(img)
        cx = self.width // 2

        if label:
            draw.text(
                (cx, 60), label, font=self.fonts["label"],
                anchor="mm", fill=self.dim_color,
            )

        # English — upper portion
        draw.text(
            (cx, 300), english,
            font=self.fonts["en_large"], anchor="mm", fill=self.accent_color,
        )

        # Divider
        draw.line([(cx - 200, 400), (cx + 200, 400)], fill="#333333", width=2)

        # Japanese — lower portion
        draw.text(
            (cx, 520), japanese,
            font=self.fonts["jp_large"], anchor="mm", fill=self.text_color,
        )

        parts = [p for p in (kana, romaji) if p]
        if parts:
            annotation = "  ·  ".join(parts)
            draw.text(
                (cx, 640), annotation,
                font=self.fonts["en_medium"], anchor="mm", fill=self.dim_color,
            )

        self._draw_progress_bar(draw, self.height - 80, progress)
        return img


    # ------------------------------------------------------------------
    # Hungarian-English card renderers
    # ------------------------------------------------------------------
    # English is the target language (shown prominently).
    # Hungarian is the native language (shown smaller, below).
    # Pronunciation guides use a distinct colour.

    def render_hun_card(
        self,
        hungarian: str,
        pronunciation: str = "",
        label: str = "",
        progress: float = 0.0,
    ) -> Image.Image:
        """Render a Hungarian-only card (native language prompt)."""
        img = Image.new("RGB", (self.width, self.height), self.bg_color)
        draw = ImageDraw.Draw(img)
        cx = self.width // 2

        if label:
            draw.text(
                (cx, 60), label, font=self.fonts["label"],
                anchor="mm", fill=self.dim_color,
            )

        draw.text(
            (cx, self.height // 2 - 40), hungarian,
            font=self.fonts["hun_native_medium"], anchor="mm",
            fill=self.text_color,
        )

        if pronunciation:
            draw.text(
                (cx, self.height // 2 + 40), pronunciation,
                font=self.fonts["hun_pron"], anchor="mm",
                fill=self.accent_color,
            )

        self._draw_progress_bar(draw, self.height - 80, progress)
        return img

    def render_hun_bilingual_card(
        self,
        english: str,
        hungarian: str,
        pronunciation: str = "",
        label: str = "",
        progress: float = 0.0,
    ) -> Image.Image:
        """Render an EN+HU bilingual card (English prominent, Hungarian below)."""
        img = Image.new("RGB", (self.width, self.height), self.bg_color)
        draw = ImageDraw.Draw(img)
        cx = self.width // 2

        if label:
            draw.text(
                (cx, 60), label, font=self.fonts["label"],
                anchor="mm", fill=self.dim_color,
            )

        # English — prominent, upper portion
        draw.text(
            (cx, 300), english,
            font=self.fonts["hun_target_large"], anchor="mm",
            fill=self.accent_color,
        )

        # Divider
        draw.line([(cx - 200, 420), (cx + 200, 420)], fill="#333333", width=2)

        # Hungarian — smaller, lower portion
        draw.text(
            (cx, 540), hungarian,
            font=self.fonts["hun_native_medium"], anchor="mm",
            fill=self.text_color,
        )

        # Pronunciation guide
        if pronunciation:
            draw.text(
                (cx, 620), pronunciation,
                font=self.fonts["hun_pron"], anchor="mm",
                fill=self.dim_color,
            )

        self._draw_progress_bar(draw, self.height - 80, progress)
        return img

    def render_hun_introduce_card(
        self,
        english: str,
        hungarian: str,
        pronunciation: str,
        step_label: str,
        progress: float = 0.0,
    ) -> Image.Image:
        """Render a Hungarian [INTRODUCE] card: Hungarian → English reveal."""
        img = Image.new("RGB", (self.width, self.height), self.bg_color)
        draw = ImageDraw.Draw(img)
        cx = self.width // 2

        # Step label
        draw.text(
            (cx, 60), f"[BEMUTATÁS]  {step_label}",
            font=self.fonts["label"], anchor="mm", fill=self.dim_color,
        )

        # Hungarian word (prompt — what the child knows)
        draw.text(
            (cx, 280), hungarian,
            font=self.fonts["hun_native_medium"], anchor="mm",
            fill=self.text_color,
        )

        # Divider
        draw.line([(cx - 200, 380), (cx + 200, 380)], fill="#333333", width=2)

        # English word (reveal — target language, prominent)
        draw.text(
            (cx, 500), english,
            font=self.fonts["hun_target_large"], anchor="mm",
            fill=self.accent_color,
        )

        # Pronunciation guide
        draw.text(
            (cx, 620), pronunciation,
            font=self.fonts["hun_pron"], anchor="mm", fill=self.dim_color,
        )

        self._draw_progress_bar(draw, self.height - 80, progress)
        return img

    def render_hun_recall_card(
        self,
        english: str,
        hungarian: str,
        pronunciation: str,
        step_label: str,
        progress: float = 0.0,
    ) -> Image.Image:
        """Render a Hungarian [RECALL] card: English → Hungarian recall."""
        img = Image.new("RGB", (self.width, self.height), self.bg_color)
        draw = ImageDraw.Draw(img)
        cx = self.width // 2

        # Step label
        draw.text(
            (cx, 60), f"[FELIDÉZÉS]  {step_label}",
            font=self.fonts["label"], anchor="mm", fill=self.dim_color,
        )

        # English word (prompt — target language)
        draw.text(
            (cx, 280), english,
            font=self.fonts["hun_target_large"], anchor="mm",
            fill=self.accent_color,
        )

        # Pronunciation
        draw.text(
            (cx, 380), pronunciation,
            font=self.fonts["hun_pron"], anchor="mm", fill=self.dim_color,
        )

        # Divider
        draw.line([(cx - 200, 440), (cx + 200, 440)], fill="#333333", width=2)

        # Hungarian (reveal — child recalls native translation)
        draw.text(
            (cx, 560), hungarian,
            font=self.fonts["hun_native_medium"], anchor="mm",
            fill=self.text_color,
        )

        self._draw_progress_bar(draw, self.height - 80, progress)
        return img

    def render_hun_translate_card(
        self,
        english: str,
        hungarian: str,
        context: str,
        step_label: str,
        progress: float = 0.0,
    ) -> Image.Image:
        """Render a Hungarian [TRANSLATE] grammar card."""
        img = Image.new("RGB", (self.width, self.height), self.bg_color)
        draw = ImageDraw.Draw(img)
        cx = self.width // 2

        # Step label
        draw.text(
            (cx, 60), f"[FORDÍTÁS]  {step_label}",
            font=self.fonts["label"], anchor="mm", fill=self.dim_color,
        )

        # Grammar context
        draw.text(
            (cx, 160), context,
            font=self.fonts["en_small"], anchor="mm", fill="#666666",
        )

        # Hungarian sentence (prompt — what the child knows)
        draw.text(
            (cx, 300), hungarian,
            font=self.fonts["hun_native_medium"], anchor="mm",
            fill=self.text_color,
        )

        # Divider
        draw.line([(cx - 300, 400), (cx + 300, 400)], fill="#333333", width=2)

        # English sentence (reveal — target language)
        draw.text(
            (cx, 540), english,
            font=self.fonts["hun_target_large"], anchor="mm",
            fill=self.accent_color,
        )

        self._draw_progress_bar(draw, self.height - 80, progress)
        return img


# Convenience function
def create_renderer(**kwargs) -> CardRenderer:
    """Create a CardRenderer with custom settings."""
    return CardRenderer(**kwargs)