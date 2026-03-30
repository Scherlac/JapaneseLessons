from importlib import import_module

from .pipeline_core import (
	CompiledItemSequence,
	LessonConfig,
	LessonContext,
	LessonRegistrationArtifact,
	NarrativeFrame,
	NarrativeVocabPlan,
	PersistedContentArtifact,
	PipelineStep,
	ReportArtifact,
	RenderedVideoArtifact,
	RetrievedMaterialArtifact,
	SelectedVocabSet,
	StepInfo,
	TouchSequence,
	VocabEnhancementArtifact,
)


_STEP_EXPORTS = {
	"CompileAssetsStep": ".compile_assets",
	"CompileTouchesStep": ".compile_touches",
	"ExtractNarrativeVocabStep": ".extract_narrative_vocab",
	"GenerateNarrativeVocabStep": ".generate_narrative_vocab",
	"NarrativeGrammarStep": ".generate_sentences",
	"GrammarSelectStep": ".grammar_select",
	"NarrativeGeneratorStep": ".narrative_generator",
	"NounPracticeStep": ".vocab_enhancement",
	"PersistContentStep": ".persist_content",
	"RegisterLessonStep": ".register_lesson",
	"RenderVideoStep": ".render_video",
	"RetrieveLessonMaterialStep": ".retrieve_material",
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
	"CompileAssetsStep",
	"CompileTouchesStep",
	"ExtractNarrativeVocabStep",
	"GenerateNarrativeVocabStep",
	"NarrativeGrammarStep",
	"GrammarSelectStep",
	"NarrativeGeneratorStep",
	"NounPracticeStep",
	"PersistContentStep",
	"RegisterLessonStep",
	"RenderVideoStep",
	"RetrieveLessonMaterialStep",
	"ReviewSentencesStep",
	"SaveReportStep",
	"SelectVocabStep",
	"VerbPracticeStep",
	"VocabEnhancementStep",
	"CompiledItemSequence",
	"LessonConfig",
	"LessonContext",
	"LessonRegistrationArtifact",
	"NarrativeFrame",
	"NarrativeVocabPlan",
	"PersistedContentArtifact",
	"PipelineStep",
	"ReportArtifact",
	"RenderedVideoArtifact",
	"RetrievedMaterialArtifact",
	"SelectedVocabSet",
	"StepInfo",
	"TouchSequence",
	"VocabEnhancementArtifact",
]
