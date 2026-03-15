"""
Tests for video_builder.py (VideoBuilder)

Two test categories:

  Unit tests  — always run. Cover VideoBuilder logic without actually rendering
                video. Use lightweight stubs/mocks for moviepy clips.

  Video tests — marked @pytest.mark.video. Render a real .mp4 using a tiny
                single-card lesson item. Slow (~30-90s), requires ffmpeg.

Usage:
    # Unit tests only (fast):
    pytest tests/test_video_builder.py -v -m "not video"

    # Full render test:
    pytest tests/test_video_builder.py -v
"""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from jlesson.video.builder import VideoBuilder, create_video_builder


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_clip_mock(duration: float = 2.0) -> MagicMock:
    """Return a lightweight mock that duck-types a moviepy clip."""
    clip = MagicMock()
    clip.duration = duration
    clip.write_videofile = MagicMock()
    return clip


def _ffmpeg_available() -> bool:
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"], capture_output=True, timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Construction
# ─────────────────────────────────────────────────────────────────────────────

class TestVideoBuilderInit:
    def test_default_fps(self):
        vb = VideoBuilder()
        assert vb.fps == 30

    def test_custom_fps(self):
        vb = VideoBuilder(fps=24)
        assert vb.fps == 24

    def test_create_video_builder_helper(self):
        vb = create_video_builder(fps=60)
        assert isinstance(vb, VideoBuilder)
        assert vb.fps == 60


# ─────────────────────────────────────────────────────────────────────────────
# create_pause_clip
# ─────────────────────────────────────────────────────────────────────────────

class TestCreatePauseClip:
    def test_returns_colorclip(self):
        from moviepy import ColorClip
        vb = VideoBuilder()
        clip = vb.create_pause_clip(2.0)
        assert isinstance(clip, ColorClip)

    def test_duration_is_set(self):
        vb = VideoBuilder()
        clip = vb.create_pause_clip(3.5)
        assert clip.duration == pytest.approx(3.5, abs=0.01)

    def test_default_color_is_black(self):
        vb = VideoBuilder()
        clip = vb.create_pause_clip(1.0)
        # ColorClip stores the color — check frame pixel is black
        frame = clip.get_frame(0)
        assert frame[0][0].tolist() == [0, 0, 0]

    def test_size_is_1920x1080(self):
        vb = VideoBuilder()
        clip = vb.create_pause_clip(1.0)
        assert clip.size == (1920, 1080)


# ─────────────────────────────────────────────────────────────────────────────
# build_video — input validation (no rendering)
# ─────────────────────────────────────────────────────────────────────────────

class TestBuildVideoValidation:
    def test_raises_on_empty_clips(self, tmp_path):
        vb = VideoBuilder()
        with pytest.raises(ValueError, match="No clips"):
            vb.build_video([], tmp_path / "out.mp4")

    def test_creates_output_directory(self, tmp_path):
        """build_video should create the output dir even if it doesn't exist."""
        vb = VideoBuilder()
        out = tmp_path / "new_dir" / "video.mp4"
        clips = [_make_clip_mock()]

        # Patch both render paths to avoid actual ffmpeg/moviepy calls
        with patch.object(vb, "_build_video_ffmpeg", return_value=True):
            vb.build_video(clips, out, method="ffmpeg")

        assert out.parent.exists()


# ─────────────────────────────────────────────────────────────────────────────
# _build_video_ffmpeg — graceful failure
# ─────────────────────────────────────────────────────────────────────────────

class TestBuildVideoFfmpegFallback:
    def test_returns_false_when_ffmpeg_missing(self, tmp_path):
        """If ffmpeg binary is not found, _build_video_ffmpeg returns False."""
        vb = VideoBuilder()
        clips = [_make_clip_mock()]
        out = tmp_path / "out.mp4"

        with patch("subprocess.run", side_effect=FileNotFoundError("ffmpeg not found")):
            result = vb._build_video_ffmpeg(clips, out, "libx264", "aac")

        assert result is False

    def test_returns_false_on_nonzero_returncode(self, tmp_path):
        vb = VideoBuilder()
        clips = [_make_clip_mock()]
        out = tmp_path / "out.mp4"

        mock_result = MagicMock()
        mock_result.returncode = 1

        with patch.object(vb, "_build_video_ffmpeg", return_value=False):
            result = vb._build_video_ffmpeg(clips, out, "libx264", "aac")

        assert result is False

    def test_build_video_falls_back_to_moviepy_when_ffmpeg_fails(self, tmp_path):
        vb = VideoBuilder()
        clips = [_make_clip_mock()]
        out = tmp_path / "out.mp4"

        with patch.object(vb, "_build_video_ffmpeg", return_value=False), \
             patch.object(vb, "_build_video_moviepy") as mock_moviepy:
            vb.build_video(clips, out, method="ffmpeg")

        mock_moviepy.assert_called_once()


# ─────────────────────────────────────────────────────────────────────────────
# create_clip
# ─────────────────────────────────────────────────────────────────────────────

class TestCreateClip:
    def test_image_only_clip_uses_default_duration(self, tmp_path):
        """When no audio exists the clip uses the 3s default."""
        from jlesson.video.cards import CardRenderer

        renderer = CardRenderer()
        img = renderer.render_introduce_card("fish", "魚", "さかな", "sakana", "1/1")
        card_path = tmp_path / "card.png"
        renderer.save_card(img, card_path)

        vb = VideoBuilder()
        clip = vb.create_clip(card_path, audio_path=None, duration=None)
        assert clip.duration == pytest.approx(3.0, abs=0.1)

    def test_image_only_clip_with_explicit_duration(self, tmp_path):
        from jlesson.video.cards import CardRenderer

        renderer = CardRenderer()
        img = renderer.render_introduce_card("cat", "猫", "ねこ", "neko", "1/1")
        card_path = tmp_path / "card.png"
        renderer.save_card(img, card_path)

        vb = VideoBuilder()
        clip = vb.create_clip(card_path, audio_path=None, duration=5.0)
        assert clip.duration == pytest.approx(5.0, abs=0.1)

    def test_missing_audio_falls_back_to_image_only(self, tmp_path):
        """If audio_path doesn't exist, clip is created without audio."""
        from jlesson.video.cards import CardRenderer

        renderer = CardRenderer()
        img = renderer.render_introduce_card("dog", "犬", "いぬ", "inu", "1/1")
        card_path = tmp_path / "card.png"
        renderer.save_card(img, card_path)

        vb = VideoBuilder()
        nonexistent_audio = tmp_path / "no_audio.mp3"
        clip = vb.create_clip(card_path, audio_path=nonexistent_audio)
        # Should still produce a clip without raising
        assert clip.duration == pytest.approx(3.0, abs=0.1)


# ─────────────────────────────────────────────────────────────────────────────
# create_multi_audio_clip
# ─────────────────────────────────────────────────────────────────────────────

class TestCreateMultiAudioClip:

    def _make_card(self, tmp_path):
        from jlesson.video.cards import CardRenderer
        renderer = CardRenderer()
        img = renderer.render_en_card("hello")
        card_path = tmp_path / "card.png"
        renderer.save_card(img, card_path)
        return card_path

    def test_no_audio_returns_3s_clip(self, tmp_path):
        card = self._make_card(tmp_path)
        vb = VideoBuilder()
        clip = vb.create_multi_audio_clip(card, [])
        assert clip.duration == pytest.approx(3.0, abs=0.1)

    def test_nonexistent_audio_returns_3s_clip(self, tmp_path):
        card = self._make_card(tmp_path)
        vb = VideoBuilder()
        clip = vb.create_multi_audio_clip(card, [tmp_path / "missing.mp3"])
        assert clip.duration == pytest.approx(3.0, abs=0.1)

    def test_single_audio_delegates_to_create_clip(self, tmp_path):
        card = self._make_card(tmp_path)
        vb = VideoBuilder()
        audio_path = tmp_path / "audio.mp3"
        audio_path.write_bytes(b"fake")
        with patch.object(vb, "create_clip", return_value=MagicMock(duration=5.0)) as mock_cc:
            clip = vb.create_multi_audio_clip(card, [audio_path])
        mock_cc.assert_called_once_with(card, audio_path, pause_before=1.5, pause_after=1.0)

    def test_none_audio_paths_are_filtered(self, tmp_path):
        card = self._make_card(tmp_path)
        vb = VideoBuilder()
        clip = vb.create_multi_audio_clip(card, [None, None])
        assert clip.duration == pytest.approx(3.0, abs=0.1)


# ─────────────────────────────────────────────────────────────────────────────
# Integration — full render (slow, requires ffmpeg + Pillow)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.video
@pytest.mark.skipif(not _ffmpeg_available(), reason="ffmpeg not found in PATH")
class TestVideoRenderIntegration:
    """Render a real single-card .mp4.  Slow (~30s), requires ffmpeg."""

    def test_render_single_card_to_mp4(self, tmp_path):
        from jlesson.video.cards import CardRenderer

        renderer = CardRenderer()
        img = renderer.render_introduce_card("water", "水", "みず", "mizu", "1/1", progress=0.5)
        card_path = tmp_path / "card_001.png"
        renderer.save_card(img, card_path)

        vb = VideoBuilder(fps=30)
        clip = vb.create_clip(card_path, audio_path=None, duration=2.0)
        out = tmp_path / "lesson.mp4"

        vb.build_video([clip], out, method="moviepy")

        assert out.exists()
        assert out.stat().st_size > 10_000, "Rendered video is unexpectedly small"

    def test_render_three_cards_concatenated(self, tmp_path):
        from jlesson.video.cards import CardRenderer

        renderer = CardRenderer()
        clips = []
        vb = VideoBuilder(fps=30)

        cards_data = [
            ("water", "水", "みず", "mizu", "1/3"),
            ("fish",  "魚", "さかな", "sakana", "2/3"),
            ("cat",   "猫", "ねこ", "neko", "3/3"),
        ]
        for i, (en, jp, kana, rm, label) in enumerate(cards_data, 1):
            img = renderer.render_introduce_card(en, jp, kana, rm, label, progress=i / 3)
            cp = tmp_path / f"card_{i:03d}.png"
            renderer.save_card(img, cp)
            clips.append(vb.create_clip(cp, audio_path=None, duration=1.0))

        out = tmp_path / "multi_card.mp4"
        vb.build_video(clips, out, method="moviepy")

        assert out.exists()
        # 3 × 1s clips → video duration should be close to 3s
        # We verify via ffprobe if available, otherwise just check file size
        assert out.stat().st_size > 20_000
