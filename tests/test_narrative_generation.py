from pathlib import Path
from unittest.mock import patch

from jlesson.curriculum import create_curriculum, get_grammar_by_id
from jlesson.item_generator import EngJapItemGenerator
from jlesson.models import NarrativeVocabBlock
from jlesson.lesson_pipeline import (
    ExtractNarrativeVocabStep,
    GenerateSentencesStep,
    GrammarSelectStep,
    LessonConfig,
    LessonContext,
    NarrativeGeneratorStep,
)
from jlesson.prompt_template import build_grammar_generate_prompt

_GEN = EngJapItemGenerator()


def test_build_grammar_generate_prompt_includes_narrative():
    grammar = [get_grammar_by_id("action_present_affirmative")]
    nouns = [
        {
            "english": "cat",
            "japanese": "ねこ",
            "kanji": "猫",
            "romaji": "neko",
        }
    ]
    verbs = [
        {
            "english": "to fly",
            "japanese": "とぶ",
            "kanji": "飛ぶ",
            "romaji": "tobu",
            "type": "う-verb",
            "masu_form": "飛びます",
        }
    ]

    from jlesson.item_generator import EngJapItemGenerator

    gen = EngJapItemGenerator()
    noun_items = [gen.convert_raw_noun(n) for n in nouns]
    verb_items = [gen.convert_raw_verb(v) for v in verbs]

    prompt = build_grammar_generate_prompt(
        grammar_specs=grammar,
        nouns=noun_items,
        verbs=verb_items,
        sentences_per_grammar=2,
        narrative="Kiki arrives in a seaside town and starts her delivery service.",
    )

    assert "NARRATIVE CONTEXT" in prompt
    assert "Kiki arrives in a seaside town" in prompt


def test_generate_sentences_passes_explicit_narrative_to_prompt(tmp_path: Path):
    config = LessonConfig(
        theme="kikis delivery service",
        curriculum_path=tmp_path / "curriculum.json",
        narrative=["Introduce Kiki and her neighborhood."],
        verbose=False,
    )
    ctx = LessonContext(config=config)
    ctx.curriculum = create_curriculum("Test")
    ctx.narrative_blocks = ["Introduce Kiki and her neighborhood."]
    ctx.nouns = [_GEN.convert_raw_noun({"english": "cat", "japanese": "ねこ", "kanji": "猫", "romaji": "neko"})]
    ctx.verbs = [_GEN.convert_raw_verb({
        "english": "to fly",
        "japanese": "とぶ",
        "kanji": "飛ぶ",
        "romaji": "tobu",
        "type": "う-verb",
        "masu_form": "飛びます",
    })]
    ctx.selected_grammar = [get_grammar_by_id("action_present_affirmative")]

    with patch(
        "jlesson.lesson_pipeline.generate_sentences.step.build_grammar_sentences_prompt",
        return_value="PROMPT",
    ) as mock_builder, patch(
        "jlesson.lesson_pipeline.generate_sentences.step.PipelineRuntime.ask_llm",
        return_value={"sentences": []},
    ):
        GenerateSentencesStep().execute(ctx)

    assert mock_builder.call_args.kwargs["narrative"] == "Introduce Kiki and her neighborhood."


def test_narrative_generator_uses_explicit_block_list(tmp_path: Path):
    config = LessonConfig(
        theme="kikis delivery service",
        curriculum_path=tmp_path / "curriculum.json",
        narrative=["Block A", "Block B"],
        lesson_blocks=2,
        verbose=False,
    )
    ctx = LessonContext(config=config)
    ctx.curriculum = create_curriculum("Test")

    NarrativeGeneratorStep().execute(ctx)

    assert ctx.narrative_blocks == ["Block A", "Block B"]


def test_narrative_generator_falls_back_to_default_blocks_when_llm_empty(tmp_path: Path):
    config = LessonConfig(
        theme="kikis delivery service",
        curriculum_path=tmp_path / "curriculum.json",
        lesson_blocks=2,
        verbose=False,
    )
    ctx = LessonContext(config=config)
    ctx.curriculum = create_curriculum("Test")

    from jlesson.lesson_pipeline.narrative_generator.config import NarrativeGeneratorLanguageConfig

    builder_calls = []

    def mock_builder(theme: str, lesson_number: int, block_count: int) -> list[str]:
        builder_calls.append((theme, lesson_number, block_count))
        return ["Auto block 1", "Auto block 2"]

    mock_step_config = NarrativeGeneratorLanguageConfig(
        source_language_label="English",
        default_block_builder=mock_builder,
    )

    with patch(
        "jlesson.lesson_pipeline.narrative_generator.step.build_narrative_generator_language_config",
        return_value=mock_step_config,
    ), patch(
        "jlesson.lesson_pipeline.narrative_generator.step.PipelineRuntime.ask_llm",
        return_value={"blocks": []},
    ):
        NarrativeGeneratorStep().execute(ctx)

    assert len(builder_calls) == 1
    assert ctx.narrative_blocks == ["Auto block 1", "Auto block 2"]


def test_extract_narrative_vocab_stores_block_terms(tmp_path: Path):
    config = LessonConfig(
        theme="kikis delivery service",
        curriculum_path=tmp_path / "curriculum.json",
        lesson_blocks=2,
        num_nouns=2,
        num_verbs=1,
        verbose=False,
    )
    ctx = LessonContext(config=config)
    ctx.curriculum = create_curriculum("Test")
    ctx.narrative_blocks = ["Kiki meets Jiji.", "Kiki flies to the bakery."]

    with patch.object(
        ctx.language_config.prompts,
        "build_narrative_vocab_extract_prompt",
        return_value="PROMPT",
    ), patch(
        "jlesson.lesson_pipeline.PipelineGadgets.ask_llm",
        return_value={
            "blocks": [
                {"index": 1, "nouns": ["Kiki", "Jiji"], "verbs": ["meet"]},
                {"index": 2, "nouns": ["bakery"], "verbs": ["fly"]},
            ]
        },
    ):
        ExtractNarrativeVocabStep().execute(ctx)

    assert ctx.narrative_vocab_terms == [
        NarrativeVocabBlock(nouns=["Kiki", "Jiji"], verbs=["meet"]),
        NarrativeVocabBlock(nouns=["bakery"], verbs=["fly"]),
    ]


def test_grammar_select_builds_block_progression(tmp_path: Path):
    config = LessonConfig(
        theme="kikis delivery service",
        curriculum_path=tmp_path / "curriculum.json",
        lesson_blocks=3,
        grammar_points_per_lesson=3,
        grammar_points_per_block=1,
        verbose=False,
    )
    ctx = LessonContext(config=config)
    ctx.curriculum = create_curriculum("Test")
    ctx.nouns = [_GEN.convert_raw_noun({"english": "cat", "japanese": "ねこ", "kanji": "猫", "romaji": "neko"})]
    ctx.verbs = [_GEN.convert_raw_verb({
        "english": "to fly",
        "japanese": "とぶ",
        "kanji": "飛ぶ",
        "romaji": "tobu",
        "type": "う-verb",
        "masu_form": "飛びます",
    })]

    selected_ids = [
        "identity_present_affirmative",
        "action_present_affirmative",
        "existence_arimasu",
    ]
    with patch(
        "jlesson.lesson_pipeline.PipelineGadgets.ask_llm",
        return_value={"selected_ids": selected_ids},
    ):
        GrammarSelectStep().execute(ctx)

    assert [[g.id for g in block] for block in ctx.selected_grammar_blocks] == [
        ["identity_present_affirmative"],
        ["action_present_affirmative"],
        ["existence_arimasu"],
    ]


def test_generate_sentences_uses_block_specific_grammar_plan(tmp_path: Path):
    config = LessonConfig(
        theme="kikis delivery service",
        curriculum_path=tmp_path / "curriculum.json",
        lesson_blocks=2,
        num_nouns=1,
        num_verbs=1,
        verbose=False,
    )
    ctx = LessonContext(config=config)
    ctx.curriculum = create_curriculum("Test")
    ctx.narrative_blocks = ["Block 1 narrative", "Block 2 narrative"]
    ctx.nouns = [
        _GEN.convert_raw_noun({"english": "cat", "japanese": "ねこ", "kanji": "猫", "romaji": "neko"}),
        _GEN.convert_raw_noun({"english": "broom", "japanese": "ほうき", "kanji": "箒", "romaji": "houki"}),
    ]
    ctx.verbs = [
        _GEN.convert_raw_verb({
            "english": "to fly",
            "japanese": "とぶ",
            "kanji": "飛ぶ",
            "romaji": "tobu",
            "type": "う-verb",
            "masu_form": "飛びます",
        }),
        _GEN.convert_raw_verb({
            "english": "to clean",
            "japanese": "そうじする",
            "kanji": "掃除する",
            "romaji": "souji suru",
            "type": "irregular",
            "masu_form": "掃除します",
        }),
    ]
    grammar_a = get_grammar_by_id("identity_present_affirmative")
    grammar_b = get_grammar_by_id("action_present_affirmative")
    ctx.selected_grammar = [grammar_a, grammar_b]
    ctx.selected_grammar_blocks = [[grammar_a], [grammar_b]]

    with patch(
        "jlesson.lesson_pipeline.generate_sentences.step.build_grammar_sentences_prompt",
        return_value="PROMPT",
    ) as mock_builder, patch(
        "jlesson.lesson_pipeline.generate_sentences.step.PipelineRuntime.ask_llm",
        return_value={"sentences": []},
    ):
        GenerateSentencesStep().execute(ctx)

    first_call = mock_builder.call_args_list[0].args[0]
    second_call = mock_builder.call_args_list[1].args[0]
    assert [g.id for g in first_call] == ["identity_present_affirmative"]
    assert [g.id for g in second_call] == ["action_present_affirmative"]
