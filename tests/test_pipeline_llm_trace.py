import json

from jlesson.curriculum import CurriculumData
from jlesson.lesson_pipeline.pipeline_orchestrator import run_pipeline
from jlesson.pipeline_steps.pipeline_core import ActionConfig, ActionStep, LessonConfig, LessonContext, StepAction


class _TraceAction(StepAction[str, dict]):
    def run(self, config: ActionConfig, chunk: str) -> dict:
        return config.runtime.call_llm(chunk, effort="medium")


class _TraceStep(ActionStep[str, dict]):
    name = "trace_step"
    description = "Trace step"

    @property
    def action(self) -> StepAction[str, dict]:
        return _TraceAction()

    def should_skip(self, ctx: LessonContext) -> bool:
        return False

    def build_input(self, ctx: LessonContext) -> str:
        return "prompt from pipeline"

    def merge_output(self, ctx: LessonContext, outputs: dict) -> LessonContext:
        ctx.trace_output = outputs
        return ctx


def test_run_pipeline_writes_llm_trace_file(tmp_path, monkeypatch):
    import jlesson.llm_cache as cache_mod

    monkeypatch.setattr(cache_mod, "ask_llm_json_free", lambda prompt, effort=None: {"prompt": prompt, "effort": effort})

    config = LessonConfig(
        theme="traceability",
        curriculum_path=tmp_path / "curriculum.json",
        output_dir=tmp_path,
        lesson_number=1,
        use_cache=True,
        verbose=False,
    )

    run_pipeline(
        config,
        pipeline=[_TraceStep()],
        load_curriculum_fn=lambda _path: CurriculumData(),
    )

    llm_trace_path = tmp_path / config.language / config.theme / "lesson_001" / "steps" / "trace_step" / "llm_cache.json"
    payload = json.loads(llm_trace_path.read_text(encoding="utf-8"))

    assert payload["step"] == "trace_step"
    assert len(payload["calls"]) == 1
    call = payload["calls"][0]
    assert call["call_index"] == 1
    assert call["step_name"] == "trace_step"
    assert call["step_index"] == 1
    assert call["cache_key"] == call["prompt_hash"]
    assert call["response_hash"]
    assert call["effort"] == "medium"