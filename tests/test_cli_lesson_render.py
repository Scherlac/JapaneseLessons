from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from jlesson.cli import cli


def _make_mock_ctx(video_path=None):
    ctx = MagicMock()
    ctx.video_path = video_path or Path("output") / "lesson.mp4"
    return ctx


class TestLessonUpdateFromStep:
    """lesson update LESSON_ID --from-step <step> uses the checkpoint pipeline."""

    def test_from_step_render_video_invokes_pipeline(self):
        runner = CliRunner()

        with patch(
            "jlesson.lesson_pipeline.run_pipeline",
            return_value=_make_mock_ctx(),
        ) as mock_run:
            result = runner.invoke(cli, ["lesson", "update", "1", "--from-step", "render_video"])

        assert result.exit_code == 0, result.output
        mock_run.assert_called_once()
        cfg = mock_run.call_args.args[0]
        assert cfg.regenerate_lesson_id == 1
        assert cfg.from_step == "render_video"

    def test_from_step_compile_assets_sets_correct_step(self):
        runner = CliRunner()

        with patch(
            "jlesson.lesson_pipeline.run_pipeline",
            return_value=_make_mock_ctx(),
        ) as mock_run:
            result = runner.invoke(cli, ["lesson", "update", "3", "--from-step", "compile_assets"])

        assert result.exit_code == 0, result.output
        cfg = mock_run.call_args.args[0]
        assert cfg.from_step == "compile_assets"
        assert cfg.regenerate_lesson_id == 3

    def test_from_step_forwards_profile_and_language(self):
        runner = CliRunner()

        with patch(
            "jlesson.lesson_pipeline.run_pipeline",
            return_value=_make_mock_ctx(),
        ) as mock_run:
            result = runner.invoke(
                cli,
                [
                    "lesson", "update", "2",
                    "--from-step", "render_video",
                    "--profile", "active_flash_cards",
                    "--language", "hun-eng",
                ],
            )

        assert result.exit_code == 0, result.output
        cfg = mock_run.call_args.args[0]
        assert cfg.profile == "active_flash_cards"
        assert cfg.language == "hun-eng"

    def test_from_step_surfaces_friendly_errors(self):
        runner = CliRunner()
        with patch(
            "jlesson.lesson_pipeline.run_pipeline",
            side_effect=ValueError("No content found for lesson 99"),
        ):
            result = runner.invoke(cli, ["lesson", "update", "99", "--from-step", "render_video"])

        assert result.exit_code != 0
        assert "No content found" in result.output

    def test_lesson_update_requires_theme_without_from_step(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["lesson", "update", "1"])
        assert result.exit_code != 0
        assert "--theme" in result.output or "theme" in result.output.lower()


class TestLessonRenderCommand:
    """Backward-compatible deprecated alias — delegates to pipeline via --from-step."""

    def test_lesson_render_invokes_pipeline(self):
        runner = CliRunner()

        with patch(
            "jlesson.lesson_pipeline.run_pipeline",
            return_value=_make_mock_ctx(),
        ) as mock_run:
            result = runner.invoke(cli, ["lesson", "render", "1"])

        assert result.exit_code == 0, result.output
        mock_run.assert_called_once()
        cfg = mock_run.call_args.args[0]
        assert cfg.regenerate_lesson_id == 1
        assert cfg.from_step == "render_video"

    def test_lesson_render_recompile_cards_uses_compile_assets(self):
        runner = CliRunner()

        with patch(
            "jlesson.lesson_pipeline.run_pipeline",
            return_value=_make_mock_ctx(),
        ) as mock_run:
            result = runner.invoke(cli, ["lesson", "render", "2", "--recompile-cards"])

        assert result.exit_code == 0, result.output
        cfg = mock_run.call_args.args[0]
        assert cfg.from_step == "compile_assets"

    def test_lesson_render_forwards_profile_and_language(self):
        runner = CliRunner()

        with patch(
            "jlesson.lesson_pipeline.run_pipeline",
            return_value=_make_mock_ctx(),
        ) as mock_run:
            result = runner.invoke(
                cli,
                [
                    "lesson", "render", "2",
                    "--profile", "active_flash_cards",
                    "--language", "hun-eng",
                ],
            )

        assert result.exit_code == 0, result.output
        cfg = mock_run.call_args.args[0]
        assert cfg.profile == "active_flash_cards"
        assert cfg.language == "hun-eng"

    def test_lesson_render_surfaces_friendly_errors(self):
        runner = CliRunner()
        with patch(
            "jlesson.lesson_pipeline.run_pipeline",
            side_effect=ValueError("No content found"),
        ):
            result = runner.invoke(cli, ["lesson", "render", "99"])

        assert result.exit_code != 0
        assert "No content found" in result.output

