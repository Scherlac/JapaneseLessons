from __future__ import annotations

import json
import time
from pathlib import Path

from jlesson.language_config import get_language_config
from jlesson.llm_cache import StepLlmCacheLog
from jlesson.pipeline_steps.pipeline_core import LessonConfig, LessonContext, PipelineStep, StepInfo

# ---------------------------------------------------------------------------
# JSON serialisation helpers (Path-safe, non-raising)
# ---------------------------------------------------------------------------

def _to_json_safe(obj):
    """Recursively convert obj into a JSON-serialisable value."""
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, dict):
        return {k: _to_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_json_safe(i) for i in obj]
    if hasattr(obj, "model_dump"):
        try:
            return obj.model_dump(mode="json")
        except Exception:
            return repr(obj)
    try:
        from dataclasses import asdict, is_dataclass
        if is_dataclass(obj) and not isinstance(obj, type):
            return _to_json_safe(asdict(obj))
    except Exception:
        pass
    try:
        json.dumps(obj)
        return obj
    except (TypeError, ValueError):
        return repr(obj)


# ---------------------------------------------------------------------------
# Step artifact helpers
# ---------------------------------------------------------------------------

def _step_artifact_dir(ctx: LessonContext, step_name: str) -> Path | None:
    """Return ``lesson_dir/steps/<step_name>`` or None when output dir is unknown."""
    from jlesson.lesson_pipeline.pipeline_paths import resolve_lesson_dir
    try:
        return resolve_lesson_dir(ctx.config) / "steps" / step_name
    except Exception:
        return None


def _save_step_artifacts(ctx: LessonContext, step_name: str, chunks, outputs) -> None:
    """Write ``steps/<step_name>/input.json``, ``output.json``, and LLM traces."""
    artifact_dir = _step_artifact_dir(ctx, step_name)
    if artifact_dir is None:
        return
    try:
        artifact_dir.mkdir(parents=True, exist_ok=True)
        if chunks:
            (artifact_dir / "input.json").write_text(
                json.dumps(_to_json_safe(chunks), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        if outputs:
            (artifact_dir / "output.json").write_text(
                json.dumps(_to_json_safe(outputs), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        llm_trace_path = artifact_dir / "llm_cache.json"
        llm_traces = list(ctx.llm_traces)
        if llm_traces:
            llm_trace_payload = StepLlmCacheLog(step=step_name, calls=llm_traces)
            llm_trace_path.write_text(
                json.dumps(_to_json_safe(llm_trace_payload), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        elif llm_trace_path.exists():
            llm_trace_path.unlink()
    except Exception:
        pass  # artifact writing is best-effort; never break the pipeline


# ---------------------------------------------------------------------------
# Context restoration from checkpoint
# ---------------------------------------------------------------------------

def restore_context_from_checkpoint(
    config: LessonConfig,
    *,
    load_curriculum_fn,
    wire_assets: bool = True,
) -> LessonContext:
    """Load a saved lesson checkpoint and return a renderable LessonContext.

    Sets ctx fields so that all LLM-generating steps naturally skip via their
    ``should_skip`` guards, and only the render sub-pipeline executes.

    Args:
        config: LessonConfig with ``regenerate_lesson_id`` set.
        load_curriculum_fn: callable returning ``CurriculumData``.
        wire_assets: when True, resolve existing asset files from disk
            (so ``compile_assets`` skips).  Pass ``False`` to force full
            asset recompilation from ``--from-step compile_assets``.
    """
    from jlesson.lesson_store import load_lesson_content
    from jlesson.lesson_pipeline.pipeline_paths import resolve_lesson_dir
    from jlesson.models import Phase, GrammarItem, GeneralItem
    from jlesson.pipeline_steps.pipeline_core import (
        CanonicalLessonBlock,
        CanonicalLessonPlan,
        LessonBlock,
        LessonPlan,
        NarrativeBlock,
        NarrativeFrame,
    )

    lesson_id = config.regenerate_lesson_id
    if lesson_id is None:
        raise ValueError("restore_context_from_checkpoint requires regenerate_lesson_id")

    lesson_dir = resolve_lesson_dir(config)
    content = load_lesson_content(lesson_id, lesson_dir)

    ctx = LessonContext(config=config)
    ctx.language_config = get_language_config(config.language)
    ctx.curriculum = load_curriculum_fn(config.curriculum_path)

    # --- Restore narrative_frame ---
    if content.narrative_blocks:
        ctx.narrative_frame = NarrativeFrame(
            theme=config.theme,
            lesson_number=config.lesson_number,
            lesson_blocks=config.lesson_blocks,
            seed_blocks=[],
            blocks=content.narrative_blocks,
        )

    # --- Restore canonical_plan (minimal stub so planning steps skip) ---
    canonical_blocks = [
        CanonicalLessonBlock(
            theme=config.theme,
            lesson_number=config.lesson_number,
            block_index=i,
            grammar_ids=content.grammar_ids,
            content_sequences={},
        )
        for i in range(config.lesson_blocks)
    ]
    ctx.canonical_plan = CanonicalLessonPlan(
        theme=config.theme,
        lesson_number=config.lesson_number,
        blocks=canonical_blocks,
    )

    # --- Restore lesson_plan from persisted words ---
    nouns = [w for w in content.words if w.phase == Phase.NOUNS]
    verbs = [w for w in content.words if w.phase == Phase.VERBS]
    adjectives = [w for w in content.words if w.phase == Phase.ADJECTIVES]
    sentences = list(content.sentences)

    lesson_blocks = [
        LessonBlock(
            block_index=i,
            content_sequences={
                Phase.NOUNS: [n for n in nouns if n.block_index == i],
                Phase.VERBS: [v for v in verbs if v.block_index == i],
                Phase.ADJECTIVES: [a for a in adjectives if a.block_index == i],
                Phase.GRAMMAR: [s for s in sentences if s.block_index == i],
            },
        )
        for i in range(config.lesson_blocks)
    ]
    ctx.lesson_plan = LessonPlan(
        theme=config.theme,
        lesson_number=config.lesson_number,
        blocks=lesson_blocks,
    )

    return ctx


# ---------------------------------------------------------------------------
# Main pipeline runner
# ---------------------------------------------------------------------------

def run_pipeline(
    config: LessonConfig,
    *,
    pipeline: list[PipelineStep],
    load_curriculum_fn,
) -> LessonContext:
    """Run the lesson generation pipeline.

    When ``config.from_step`` is set, load the existing checkpoint and run only
    the render sub-pipeline (compile_assets → compile_touches → render_video →
    save_report), skipping all LLM-generation steps.
    """
    if config.from_step is not None:
        wire_assets = config.from_step != "compile_assets"
        ctx = restore_context_from_checkpoint(
            config,
            load_curriculum_fn=load_curriculum_fn,
            wire_assets=wire_assets,
        )
        _render_steps = {"compile_assets", "compile_touches", "render_video", "save_report"}
        pipeline = [s for s in pipeline if s.name in _render_steps]
    else:
        ctx = LessonContext(config=config)
        ctx.language_config = get_language_config(config.language)
        ctx.curriculum = load_curriculum_fn(config.curriculum_path)

    # Open RCM store if a path was configured
    _rcm_store = None
    if config.rcm_path is not None:
        from jlesson.rcm import RCMStore
        _rcm_store = RCMStore(config.rcm_path / "rcm.db")
        ctx.rcm = _rcm_store
        # Register the target-language dim map so grammar dims are populated on write
        if hasattr(ctx, "language_config") and ctx.language_config is not None:
            target_dim_map = ctx.language_config.target.rcm_dim_map
            if target_dim_map:
                _rcm_store.register_dim_map(config.language, target_dim_map)

    total = len(pipeline)

    print(f"\n{'=' * 60}")
    print(f"  LESSON: {config.theme.upper()}")
    if config.from_step:
        print(f"  RESUME : from {config.from_step}")
    print(f"{'=' * 60}")

    t_total = time.time()
    for index, step in enumerate(pipeline, 1):
        info = StepInfo(
            index=index,
            total=total,
            name=step.name,
            description=step.description,
        )
        ctx.step_info = info
        ctx.llm_traces.clear()
        if config.verbose:
            print(f"\n  {info.label} {step.description}")

        t_step = time.time()
        ctx = step.execute(ctx)

        _chunks = getattr(step, "_last_chunks", [])
        _outputs = getattr(step, "_last_outputs", [])
        step_elapsed = time.time() - t_step
        ctx.report.record_time(step.name, step_elapsed)
        ctx.report.record_llm_usage(step.name, list(ctx.llm_traces))

        _save_step_artifacts(ctx, step.name, _chunks, _outputs)

    elapsed = time.time() - t_total
    print(f"\n  Done - {elapsed:.0f}s")

    video_path = ctx.rendered_video.video_path if ctx.rendered_video else None
    report_path = ctx.saved_report.report_path if ctx.saved_report else None

    if video_path and video_path.exists():
        print(f"  Video   : {video_path}")
    if report_path:
        print(f"  Report  : {report_path}")

    if _rcm_store is not None:
        _rcm_store.close()

    return ctx
