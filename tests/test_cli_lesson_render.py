from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from jlesson.cli import cli


class TestLessonRenderCommand:
    def test_lesson_render_invokes_helper(self):
        runner = CliRunner()
        expected_path = Path("output") / "lesson_001_kikis delivery service.mp4"

        with patch(
            "jlesson.lesson_pipeline.render_existing_lesson",
            return_value=expected_path,
        ) as mock_render:
            result = runner.invoke(cli, ["lesson", "render", "1"])

        assert result.exit_code == 0
        assert "Video rendered:" in result.output
        mock_render.assert_called_once()
        assert mock_render.call_args.kwargs["lesson_id"] == 1
        assert mock_render.call_args.kwargs["profile"] == "passive_video"

    def test_lesson_render_forwards_options(self):
        runner = CliRunner()
        expected_path = Path("tmp") / "video.mp4"

        with patch(
            "jlesson.lesson_pipeline.render_existing_lesson",
            return_value=expected_path,
        ) as mock_render:
            result = runner.invoke(
                cli,
                [
                    "lesson",
                    "render",
                    "2",
                    "--output-dir",
                    "custom_output",
                    "--profile",
                    "active_flash_cards",
                    "--language",
                    "hun-eng",
                ],
            )

        assert result.exit_code == 0
        call = mock_render.call_args.kwargs
        assert call["lesson_id"] == 2
        assert call["output_dir"] == Path("custom_output")
        assert call["profile"] == "active_flash_cards"
        assert call["language"] == "hun-eng"

    def test_lesson_render_surfaces_friendly_errors(self):
        runner = CliRunner()
        with patch(
            "jlesson.lesson_pipeline.render_existing_lesson",
            side_effect=ValueError("No content found"),
        ):
            result = runner.invoke(cli, ["lesson", "render", "99"])

        assert result.exit_code != 0
        assert "No content found" in result.output
