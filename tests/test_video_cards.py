"""
Tests for video_cards.py (CardRenderer)

All tests are pure-unit: Pillow renders in memory, no network, no subprocess.

Usage:
    pytest tests/test_video_cards.py -v
"""

import pytest
from pathlib import Path
from PIL import Image

from jlesson.models import GeneralItem, Phase, Touch, TouchIntent, TouchType
from jlesson.video.cards import CardRenderer, create_renderer


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
        expected_keys = {
            "jp_large", "jp_medium", "jp_small", "en_large", "en_medium", "en_small", "label",
            "hun_target_large", "hun_native_medium", "hun_pron",
        }
        assert expected_keys == set(renderer.fonts.keys())

    def test_create_renderer_helper(self):
        r = create_renderer(bg_color="#000000")
        assert isinstance(r, CardRenderer)
        assert r.bg_color == "#000000"

    def test_wrap_text_breaks_long_spaced_text(self, renderer):
        wrapped = renderer._wrap_text_to_width(
            "This is a deliberately long source sentence that should wrap before it reaches the edge of the card.",
            renderer.fonts["en_large"],
            420,
        )
        assert "\n" in wrapped

    def test_wrap_text_breaks_long_unspaced_text(self, renderer):
        wrapped = renderer._wrap_text_to_width(
            "これはとても長い日本語の文章で自動改行が必要ですこれはとても長い日本語の文章で自動改行が必要です",
            renderer.fonts["jp_medium"],
            420,
        )
        assert "\n" in wrapped


# ─────────────────────────────────────────────────────────────────────────────
# render_card
# ─────────────────────────────────────────────────────────────────────────────

class TestRenderCard:
    def test_returns_pil_image(self, renderer):
        img = renderer.render_card(_make_item(), touch=None)
        assert isinstance(img, Image.Image)

    def test_correct_size(self, renderer):
        img = renderer.render_card(_make_item(), touch=None)
        assert img.size == (1920, 1080)

    def test_rgb_mode(self, renderer):
        img = renderer.render_card(_make_item(), touch=None)
        assert img.mode == "RGB"

    def test_background_color_applied(self, renderer):
        img = renderer.render_card(_make_item(), touch=None)
        bg_rgb = _hex_to_rgb(renderer.bg_color)
        assert img.getpixel((0, 0)) == bg_rgb

    def test_progress_zero_no_accent_bar(self, renderer):
        img = renderer.render_card(_make_item(), touch=None, progress=0.0)
        accent_rgb = _hex_to_rgb(renderer.accent_color)
        bar_y = renderer.height - 80 + 3
        bar_x = renderer.width // 2 + 200
        assert img.getpixel((bar_x, bar_y)) != accent_rgb

    def test_progress_partial_fills_left_half(self, renderer):
        img = renderer.render_card(_make_item(), touch=None, progress=0.5)
        accent_rgb = _hex_to_rgb(renderer.accent_color)
        bar_y = renderer.height - 80 + 3
        bar_x_left = (renderer.width - 800) // 2 + 50
        assert img.getpixel((bar_x_left, bar_y)) == accent_rgb
        bar_x_right = (renderer.width - 800) // 2 + 750
        assert img.getpixel((bar_x_right, bar_y)) != accent_rgb

    @pytest.mark.parametrize(
        "intent",
        [
            TouchIntent.INTRODUCE,
            TouchIntent.RECALL,
            TouchIntent.TRANSLATE,
            TouchIntent.CONFIRM,
            TouchIntent.UNKNOWN,
        ],
    )
    def test_supported_intents_do_not_crash(self, renderer, intent):
        renderer.render_card(_make_item(), touch=_make_touch(intent))

    def test_long_text_does_not_crash(self, renderer):
        renderer.render_card(
            _make_item(
                source="This is a very long English sentence that should still render without error.",
                target="これはかなり長い日本語のテキストで、描画前に幅を測って自動改行しないとカード領域をはみ出してしまいます。",
                pronunciation="Kore wa kanari nagai nihongo no tekisuto de, byouga mae ni haba o hatte jidou kaigyou shinai to kaado ryouiki o hamidashite shimaimasu.",
            ),
            touch=None,
            label="3/30",
        )

    def test_long_extra_field_does_not_crash(self, renderer):
        item = _make_item(source="water", target="水", pronunciation="みず")
        item.target.extra["note"] = (
            "This is an extra field with enough content to require wrapping when it is drawn "
            "under the main target block."
        )
        renderer.render_card(item, touch=None)


# ─────────────────────────────────────────────────────────────────────────────
# save_card
# ─────────────────────────────────────────────────────────────────────────────

class TestSaveCard:
    def test_creates_file(self, renderer, tmp_path):
        img = renderer.render_card(_make_item(source="fish", target="魚", pronunciation="さかな"), touch=None)
        out = tmp_path / "card_001.png"
        renderer.save_card(img, out)
        assert out.exists()

    def test_file_is_nonzero(self, renderer, tmp_path):
        img = renderer.render_card(_make_item(source="fish", target="魚", pronunciation="さかな"), touch=None)
        out = tmp_path / "card_001.png"
        renderer.save_card(img, out)
        assert out.stat().st_size > 0

    def test_saved_file_is_readable_png(self, renderer, tmp_path):
        img = renderer.render_card(_make_item(source="fish", target="魚", pronunciation="さかな"), touch=None)
        out = tmp_path / "card_001.png"
        renderer.save_card(img, out)
        loaded = Image.open(out)
        assert loaded.format == "PNG"
        assert loaded.size == (1920, 1080)

    def test_creates_parent_directories(self, renderer, tmp_path):
        out = tmp_path / "subdir" / "deep" / "card.png"
        img = renderer.render_card(_make_item(source="test", target="テスト", pronunciation="てすと"), touch=None)
        renderer.save_card(img, out)
        assert out.exists()

    def test_save_cards_for_multiple_intents(self, renderer, tmp_path):
        """Smoke-test: generic cards for multiple intents can be saved."""
        cards = [
            ("introduce", renderer.render_card(_make_item(source="cat", target="猫", pronunciation="ねこ"), _make_touch(TouchIntent.INTRODUCE))),
            ("recall", renderer.render_card(_make_item(source="cat", target="猫", pronunciation="ねこ"), _make_touch(TouchIntent.RECALL))),
            ("translate", renderer.render_card(_make_item(source="I see a cat.", target="猫を見ます。", pronunciation="Neko o mimasu."), _make_touch(TouchIntent.TRANSLATE))),
        ]
        for name, card in cards:
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


def _make_item(
    source: str = "water",
    target: str = "水",
    pronunciation: str = "みず",
) -> GeneralItem:
    return GeneralItem.model_validate(
        {
            "source": {"display_text": source},
            "target": {
                "display_text": target,
                "pronunciation": pronunciation,
            },
        }
    )


def _make_touch(intent: TouchIntent) -> Touch:
    return Touch.model_validate(
        {
            "touch_index": 1,
            "phase": Phase.NOUNS,
            "item": _make_item().model_dump(),
            "touch_type": TouchType.SOURCE_TARGET,
            "intent": intent,
        }
    )
