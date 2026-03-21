from __future__ import annotations

import jlesson.video.builder as video_builder_module
from .pipeline_core import LessonContext, PipelineStep
from .pipeline_paths import resolve_output_dir


class RenderVideoStep(PipelineStep):
    """Step 11 — Assemble MP4 from touch sequence."""

    name = "render_video"
    description = "Assemble MP4 from touch sequence"

    @staticmethod
    def build_video_items(noun_items: list[dict], sentences: list[dict]) -> list[dict]:
        items = []
        total = len(noun_items) + len(sentences)

        for index, noun in enumerate(noun_items, 1):
            japanese = noun.get("japanese", "")
            romaji = noun.get("romaji", "")
            reveal = f"{japanese}  ({romaji})" if romaji else japanese
            items.append(
                {
                    "phase": "Nouns",
                    "step": "INTRODUCE",
                    "counter": f"{index}/{total}",
                    "prompt": noun.get("english", ""),
                    "reveal": reveal,
                    "tts_text": japanese,
                    "tts_voice": "ja-JP-NanamiNeural",
                }
            )

        offset = len(noun_items)
        for index, sentence in enumerate(sentences, 1):
            items.append(
                {
                    "phase": "Grammar",
                    "step": "TRANSLATE",
                    "counter": f"{offset + index}/{total}",
                    "prompt": sentence.get("english", ""),
                    "reveal": sentence.get("japanese", ""),
                    "tts_text": sentence.get("japanese", ""),
                    "tts_voice": "ja-JP-NanamiNeural",
                }
            )

        return items

    def execute(self, ctx: LessonContext) -> LessonContext:
        if not ctx.config.render_video or ctx.config.dry_run:
            reason = "dry-run" if ctx.config.dry_run else "skipped"
            self._log(ctx, f"       ({reason})")
            return ctx

        output_dir = resolve_output_dir(ctx.config)
        video_path = output_dir / f"lesson_{ctx.lesson_id:03d}_{ctx.config.theme}.mp4"

        video_builder = video_builder_module.VideoBuilder()
        clips = []
        for touch in ctx.touches:
            card_path = touch.artifacts.get("card")
            if card_path is None or not card_path.exists():
                continue
            audio_paths = touch.artifacts.get("audio") or []
            clip = video_builder.create_multi_audio_clip(card_path, audio_paths)
            clips.append(clip)

        self._log(ctx, f"       {len(clips)} clips -> {video_path.name}")

        if clips:
            video_builder.build_video(clips, video_path, method="ffmpeg")
            ctx.video_path = video_path
            size_kb = video_path.stat().st_size // 1024
            self._log(ctx, f"       OK  ({size_kb} KB)")
            ctx.report.add_artifact("Video", video_path)

        lesson_dir = output_dir / f"lesson_{ctx.lesson_id:03d}"
        cards_dir = lesson_dir / "cards"
        audio_dir = lesson_dir / "audio"
        if cards_dir.exists():
            ctx.report.add_artifact("Cards", cards_dir)
        if audio_dir.exists():
            ctx.report.add_artifact("Audio", audio_dir)
        return ctx