from importlib import import_module

from .pipeline_core import (
	CanonicalLessonPlan,
	GeneralItemSequence,
	LessonConfig,
	LessonContext,
	LessonRegistrationArtifact,
	NarrativeFrame,
	PersistedContentArtifact,
	PipelineStep,
	ReportArtifact,
	RenderedVideoArtifact,
	StepInfo,
	TouchSequence,
)


_STEP_EXPORTS = {
	"CanonicalPlannerStep": ".canonical_planner",
	"CompileAssetsStep": ".compile_assets",
	"CompileTouchesStep": ".compile_touches",
	"NarrativeGeneratorStep": ".narrative_generator",
	"PersistContentStep": ".persist_content",
	"RegisterLessonStep": ".register_lesson",
	"RenderVideoStep": ".render_video",
	"ReviewSentencesStep": ".review_sentences",
	"SaveReportStep": ".save_report",
}


def __getattr__(name: str):
	module_name = _STEP_EXPORTS.get(name)
	if module_name is None:
		raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
	module = import_module(module_name, __name__)
	value = getattr(module, name)
	globals()[name] = value
	return value



__all__ = [
	"CanonicalLessonPlan",
	"CanonicalPlannerStep",
	"CompileAssetsStep",
	"CompileTouchesStep",
	"NarrativeGeneratorStep",
	"PersistContentStep",
	"RegisterLessonStep",
	"RenderVideoStep",
	"ReviewSentencesStep",
	"SaveReportStep",
	"GeneralItemSequence",
	"LessonConfig",
	"LessonContext",
	"LessonRegistrationArtifact",
	"NarrativeFrame",
	"PersistedContentArtifact",
	"PipelineStep",
	"ReportArtifact",
	"RenderedVideoArtifact",
	"StepInfo",
	"TouchSequence",
]
