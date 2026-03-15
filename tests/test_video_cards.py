"""
Tests for video_cards.py (CardRenderer)

All tests are pure-unit: Pillow renders in memory, no network, no subprocess.

Usage:
    pytest tests/test_video_cards.py -v
"""

import pytest
from pathlib import Path
from PIL import Image

from video_cards import CardRenderer, create_renderer


# ─────────────────────────────────────────────────────────────────────────────
# Shared fixture
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def renderer() -> CardRenderer:
    """Single CardRenderer shared across the module (font loading is slow)."""
    return CardRenderer()


# ─────────────────────────────────────────────────────────────────────────────
# Construction
# ─────────────────────────────────────────────────────────────────────────────

class TestCardRendererInit:
    def test_default_dimensions(self, renderer):
        assert renderer.width == 1920
        assert renderer.height == 1080

    def test_default_colors(self, renderer):
        assert renderer.bg_color == "#1a1a2e"
        assert renderer.accent_color == "#4fc3f7"
        assert renderer.text_color == "#ffffff"

    def test_custom_dimensions(self):
        r = CardRenderer(width=1280, height=720)
        assert r.width == 1280
        assert r.height == 720

    def test_fonts_loaded(self, renderer):
        expected_keys = {"jp_large", "jp_medium", "en_large", "en_medium", "en_small", "label"}
        assert expected_keys == set(renderer.fonts.keys())

    def test_create_renderer_helper(self):
        r = create_renderer(bg_color="#000000")
        assert isinstance(r, CardRenderer)
        assert r.bg_color == "#000000"


# ─────────────────────────────────────────────────────────────────────────────
# render_introduce_card
# ─────────────────────────────────────────────────────────────────────────────

class TestRenderIntroduceCard:
    def test_returns_pil_image(self, renderer):
        img = renderer.render_introduce_card("water", "水", "みず", "mizu", "1/30")
        assert isinstance(img, Image.Image)

    def test_correct_size(self, renderer):
        img = renderer.render_introduce_card("water", "水", "みず", "mizu", "1/30")
        assert img.size == (1920, 1080)

    def test_rgb_mode(self, renderer):
        img = renderer.render_introduce_card("water", "水", "みず", "mizu", "1/30")
        assert img.mode == "RGB"

    def test_background_color_applied(self, renderer):
        img = renderer.render_introduce_card("water", "水", "みず", "mizu", "1/30")
        # Top-left corner should be the background color
        bg_rgb = _hex_to_rgb(renderer.bg_color)
        assert img.getpixel((0, 0)) == bg_rgb

    def test_progress_zero_no_accent_bar(self, renderer):
        img = renderer.render_introduce_card("water", "水", "みず", "mizu", "1/30", progress=0.0)
        # Sample the middle of the progress bar on the right half — should not be accent color
        accent_rgb = _hex_to_rgb(renderer.accent_color)
        bar_y = renderer.height - 80 + 3  # centre of 6px bar
        bar_x = renderer.width // 2 + 200  # right half
        assert img.getpixel((bar_x, bar_y)) != accent_rgb

    def test_progress_full_has_accent_bar(self, renderer):
        img = renderer.render_introduce_card("water", "水", "みず", "mizu", "1/30", progress=1.0)
        accent_rgb = _hex_to_rgb(renderer.accent_color)
        bar_y = renderer.height - 80 + 3
        bar_x = renderer.width // 2  # middle — definitely filled at progress=1.0
        assert img.getpixel((bar_x, bar_y)) == accent_rgb

    def test_unicode_japanese_does_not_crash(self, renderer):
        # Hiragana, katakana, kanji mix
        renderer.render_introduce_card("to eat", "食べます", "たべます", "tabemasu", "2/30")

    def test_long_english_does_not_crash(self, renderer):
        renderer.render_introduce_card(
            "This is a very long English sentence that should still render without error.",
            "長い英語のテスト", "ながいえいごのてすと", "Nagai eigo no tesuto", "3/30",
        )


# ─────────────────────────────────────────────────────────────────────────────
# render_recall_card
# ─────────────────────────────────────────────────────────────────────────────

class TestRenderRecallCard:
    def test_returns_pil_image(self, renderer):
        img = renderer.render_recall_card("水", "みず", "mizu", "water", "5/30")
        assert isinstance(img, Image.Image)

    def test_correct_size(self, renderer):
        img = renderer.render_recall_card("水", "みず", "mizu", "water", "5/30")
        assert img.size == (1920, 1080)

    def test_rgb_mode(self, renderer):
        img = renderer.render_recall_card("水", "みず", "mizu", "water", "5/30")
        assert img.mode == "RGB"

    def test_background_color_applied(self, renderer):
        img = renderer.render_recall_card("水", "みず", "mizu", "water", "5/30")
        bg_rgb = _hex_to_rgb(renderer.bg_color)
        assert img.getpixel((0, 0)) == bg_rgb

    def test_unicode_does_not_crash(self, renderer):
        renderer.render_recall_card("食べます", "たべます", "tabemasu", "to eat", "6/30")


# ─────────────────────────────────────────────────────────────────────────────
# render_translate_card
# ─────────────────────────────────────────────────────────────────────────────

class TestRenderTranslateCard:
    def test_returns_pil_image(self, renderer):
        img = renderer.render_translate_card(
            "I eat fish.", "魚を食べます。", "Sakana o tabemasu.",
            "I / present / affirmative", "10/30",
        )
        assert isinstance(img, Image.Image)

    def test_correct_size(self, renderer):
        img = renderer.render_translate_card(
            "I eat fish.", "魚を食べます。", "Sakana o tabemasu.",
            "I / present / affirmative", "10/30",
        )
        assert img.size == (1920, 1080)

    def test_rgb_mode(self, renderer):
        img = renderer.render_translate_card(
            "I eat fish.", "魚を食べます。", "Sakana o tabemasu.",
            "I / present / affirmative", "10/30",
        )
        assert img.mode == "RGB"

    def test_progress_partial_fills_left_half(self, renderer):
        img = renderer.render_translate_card(
            "I eat fish.", "魚を食べます。", "Sakana o tabemasu.",
            "context", "10/30", progress=0.5,
        )
        accent_rgb = _hex_to_rgb(renderer.accent_color)
        bar_y = renderer.height - 80 + 3
        # Left quarter of bar should be filled
        bar_x_left = (renderer.width - 800) // 2 + 50
        assert img.getpixel((bar_x_left, bar_y)) == accent_rgb
        # Right quarter should NOT be filled
        bar_x_right = (renderer.width - 800) // 2 + 750
        assert img.getpixel((bar_x_right, bar_y)) != accent_rgb


# ─────────────────────────────────────────────────────────────────────────────
# save_card
# ─────────────────────────────────────────────────────────────────────────────

class TestSaveCard:
    def test_creates_file(self, renderer, tmp_path):
        img = renderer.render_introduce_card("fish", "魚", "さかな", "sakana", "1/30")
        out = tmp_path / "card_001.png"
        renderer.save_card(img, out)
        assert out.exists()

    def test_file_is_nonzero(self, renderer, tmp_path):
        img = renderer.render_introduce_card("fish", "魚", "さかな", "sakana", "1/30")
        out = tmp_path / "card_001.png"
        renderer.save_card(img, out)
        assert out.stat().st_size > 0

    def test_saved_file_is_readable_png(self, renderer, tmp_path):
        img = renderer.render_introduce_card("fish", "魚", "さかな", "sakana", "1/30")
        out = tmp_path / "card_001.png"
        renderer.save_card(img, out)
        loaded = Image.open(out)
        assert loaded.format == "PNG"
        assert loaded.size == (1920, 1080)

    def test_creates_parent_directories(self, renderer, tmp_path):
        out = tmp_path / "subdir" / "deep" / "card.png"
        img = renderer.render_introduce_card("test", "テスト", "てすと", "tesuto", "1/1")
        renderer.save_card(img, out)
        assert out.exists()

    def test_save_all_card_types(self, renderer, tmp_path):
        """Smoke-test: all three card types can be saved."""
        introduce = renderer.render_introduce_card("cat", "猫", "ねこ", "neko", "1/30")
        recall = renderer.render_recall_card("猫", "ねこ", "neko", "cat", "2/30")
        translate = renderer.render_translate_card(
            "I see a cat.", "猫を見ます。", "Neko o mimasu.", "context", "3/30"
        )
        for name, card in [("introduce", introduce), ("recall", recall), ("translate", translate)]:
            out = tmp_path / f"{name}.png"
            renderer.save_card(card, out)
            assert out.exists(), f"{name} card was not saved"


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert '#rrggbb' to (r, g, b) tuple."""
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
