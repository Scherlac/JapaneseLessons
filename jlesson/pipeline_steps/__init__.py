from importlib import import_module

from .pipeline_core import (
	BlockOutline,
	CanonicalLessonPlan,
	CanonicalVocabSet,
	GeneralItemSequence,
	GrammarSelectionArtifact,
	LessonConfig,
	LessonContext,
	LessonOutline,
	LessonRegistrationArtifact,
	NarrativeFrame,
	PersistedContentArtifact,
	PipelineStep,
	ReportArtifact,
	RenderedVideoArtifact,
	VocabSet,
	StepInfo,
	TouchSequence,
	VocabEnhancementArtifact,
)


_STEP_EXPORTS = {
	"CanonicalVocabSelectStep": ".canonical_vocab_select",
	"CompileAssetsStep": ".compile_assets",
	"CompileTouchesStep": ".compile_touches",
	"ExtractNarrativeVocabStep": ".extract_narrative_vocab",
	"NarrativeGrammarStep": ".generate_sentences",
	"GrammarSelectStep": ".grammar_select",
	"LessonPlannerStep": ".lesson_planner",
	"NarrativeGeneratorStep": ".narrative_generator",
	"NounPracticeStep": ".vocab_enhancement",
	"PersistContentStep": ".persist_content",
	"RegisterLessonStep": ".register_lesson",
	"RenderVideoStep": ".render_video",
	"ReviewSentencesStep": ".review_sentences",
	"SaveReportStep": ".save_report",
	"SelectVocabStep": ".select_vocab",
	"VerbPracticeStep": ".vocab_enhancement",
	"VocabEnhancementStep": ".vocab_enhancement",
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
	"CanonicalVocabSelectStep",
	"CanonicalVocabSet",
	"CompileAssetsStep",
	"CompileTouchesStep",
	"ExtractNarrativeVocabStep",
	"GrammarSelectionArtifact",
	"NarrativeGrammarStep",
	"GrammarSelectStep",
	"LessonPlannerStep",
	"NarrativeGeneratorStep",
	"NounPracticeStep",
	"PersistContentStep",
	"RegisterLessonStep",
	"RenderVideoStep",
	"ReviewSentencesStep",
	"SaveReportStep",
	"SelectVocabStep",
	"VerbPracticeStep",
	"VocabEnhancementStep",
	"GeneralItemSequence",
	"GrammarSelectionArtifact",
	"LessonConfig",
	"LessonContext",
	"LessonRegistrationArtifact",
	"NarrativeFrame",
	"PersistedContentArtifact",
	"PipelineStep",
	"ReportArtifact",
	"RenderedVideoArtifact",
	"VocabSet",
	"StepInfo",
	"TouchSequence",
	"VocabEnhancementArtifact",
]
