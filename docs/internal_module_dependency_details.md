# Internal Module Dependency Details: jlesson

- Backend: `grimp`
- Modules: `43`
- Internal edges: `100`
- Cycle components: `0`

## Cycle Paths

- None

## Focused Boundaries

### `lesson_pipeline` <-> `video`

- Direct imports `lesson_pipeline` -> `video`: `2`
  - `jlesson.lesson_pipeline.pipeline_existing_lesson` -> `jlesson.video.builder` [...](../jlesson/lesson_pipeline/pipeline_existing_lesson.py#L12)
  - `jlesson.lesson_pipeline.render_video` -> `jlesson.video.builder` [...](../jlesson/lesson_pipeline/render_video.py#L3)
- Direct imports `video` -> `lesson_pipeline`: `0`
- Cycle nodes spanning both groups: `0`
- Cycle path `lesson_pipeline` -> `video`: none
- Cycle path `video` -> `lesson_pipeline`: none

### `lesson_pipeline` <-> `asset_compiler`

- Direct imports `lesson_pipeline` -> `asset_compiler`: `2`
  - `jlesson.lesson_pipeline.compile_assets` -> `jlesson.asset_compiler` [...](../jlesson/lesson_pipeline/compile_assets.py#L3)
  - `jlesson.lesson_pipeline.pipeline_existing_lesson` -> `jlesson.asset_compiler` [...](../jlesson/lesson_pipeline/pipeline_existing_lesson.py#L6)
- Direct imports `asset_compiler` -> `lesson_pipeline`: `0`
- Cycle nodes spanning both groups: `0`
- Cycle path `lesson_pipeline` -> `asset_compiler`: none
- Cycle path `asset_compiler` -> `lesson_pipeline`: none


## Top Transitive Dependency Paths

### `jlesson.lesson_pipeline.pipeline_existing_lesson` [...](../jlesson/lesson_pipeline/pipeline_existing_lesson.py#L1)

- `jlesson.lesson_pipeline.pipeline_existing_lesson` -> `jlesson.language_config` -> `jlesson.curriculum` [...](../jlesson/lesson_pipeline/pipeline_existing_lesson.py#L7)
- `jlesson.lesson_pipeline.pipeline_existing_lesson` -> `jlesson.language_config` -> `jlesson.prompt_template` [...](../jlesson/lesson_pipeline/pipeline_existing_lesson.py#L7)
- `jlesson.lesson_pipeline.pipeline_existing_lesson` -> `jlesson.lesson_pipeline.pipeline_core` -> `jlesson.lesson_report` [...](../jlesson/lesson_pipeline/pipeline_existing_lesson.py#L14)

### `jlesson.lesson_pipeline.save_report` [...](../jlesson/lesson_pipeline/save_report.py#L1)

- `jlesson.lesson_pipeline.save_report` -> `jlesson.lesson_pipeline.pipeline_core` -> `jlesson.language_config` -> `jlesson.curriculum` [...](../jlesson/lesson_pipeline/save_report.py#L4)
- `jlesson.lesson_pipeline.save_report` -> `jlesson.lesson_pipeline.pipeline_core` -> `jlesson.language_config` -> `jlesson.prompt_template` [...](../jlesson/lesson_pipeline/save_report.py#L4)
- `jlesson.lesson_pipeline.save_report` -> `jlesson.lesson_pipeline.pipeline_core` -> `jlesson.language_config` -> `jlesson.video.tts_engine` [...](../jlesson/lesson_pipeline/save_report.py#L4)

### `jlesson.cli` [...](../jlesson/cli.py#L1)

- `jlesson.cli` -> `jlesson.lesson_pipeline` -> `jlesson.lesson_pipeline.pipeline_existing_lesson` -> `jlesson.asset_compiler` -> `jlesson.video.cards` [...](../jlesson/cli.py#L348)
- `jlesson.cli` -> `jlesson.lesson_pipeline` -> `jlesson.lesson_pipeline.pipeline_existing_lesson` -> `jlesson.profiles` [...](../jlesson/cli.py#L348)
- `jlesson.cli` -> `jlesson.lesson_pipeline` -> `jlesson.lesson_pipeline.pipeline_existing_lesson` -> `jlesson.lesson_pipeline.pipeline_paths` [...](../jlesson/cli.py#L348)

### `jlesson.asset_compiler` [...](../jlesson/asset_compiler.py#L1)

- `jlesson.asset_compiler` -> `jlesson.language_config` -> `jlesson.curriculum` [...](../jlesson/asset_compiler.py#L20)
- `jlesson.asset_compiler` -> `jlesson.language_config` -> `jlesson.prompt_template` [...](../jlesson/asset_compiler.py#L20)
- `jlesson.asset_compiler` -> `jlesson.language_config` -> `jlesson.item_generator` [...](../jlesson/asset_compiler.py#L20)

## Direct Imports For Highest Fan-Out Modules

### `jlesson.lesson_pipeline.pipeline_existing_lesson` [...](../jlesson/lesson_pipeline/pipeline_existing_lesson.py#L1)

- `jlesson.asset_compiler` [...](../jlesson/lesson_pipeline/pipeline_existing_lesson.py#L6)
- `jlesson.language_config` [...](../jlesson/lesson_pipeline/pipeline_existing_lesson.py#L7)
- `jlesson.lesson_pipeline.pipeline_core` [...](../jlesson/lesson_pipeline/pipeline_existing_lesson.py#L14)
- `jlesson.lesson_pipeline.pipeline_paths` [...](../jlesson/lesson_pipeline/pipeline_existing_lesson.py#L15)
- `jlesson.lesson_store` [...](../jlesson/lesson_pipeline/pipeline_existing_lesson.py#L8)
- `jlesson.models` [...](../jlesson/lesson_pipeline/pipeline_existing_lesson.py#L9)
- `jlesson.profiles` [...](../jlesson/lesson_pipeline/pipeline_existing_lesson.py#L10)
- `jlesson.touch_compiler` [...](../jlesson/lesson_pipeline/pipeline_existing_lesson.py#L11)
- `jlesson.video.builder` [...](../jlesson/lesson_pipeline/pipeline_existing_lesson.py#L12)

### `jlesson.lesson_pipeline.save_report` [...](../jlesson/lesson_pipeline/save_report.py#L1)

- `jlesson.lesson_pipeline.pipeline_core` [...](../jlesson/lesson_pipeline/save_report.py#L4)
- `jlesson.lesson_pipeline.pipeline_paths` [...](../jlesson/lesson_pipeline/save_report.py#L5)
- `jlesson.lesson_report` [...](../jlesson/lesson_pipeline/save_report.py#L3)
- `jlesson.models` [...](../jlesson/lesson_pipeline/save_report.py#L9)
- `jlesson.profiles` [...](../jlesson/lesson_pipeline/save_report.py#L6)
- `jlesson.touch_compiler` [...](../jlesson/lesson_pipeline/save_report.py#L7)

### `jlesson.cli` [...](../jlesson/cli.py#L1)

- `jlesson.config` [...](../jlesson/cli.py#L56)
- `jlesson.curriculum` [...](../jlesson/cli.py#L21)
- `jlesson.language_config` [...](../jlesson/cli.py#L23)
- `jlesson.lesson_pipeline` [...](../jlesson/cli.py#L348)
- `jlesson.prompt_template` [...](../jlesson/cli.py#L24)
- `jlesson.vocab_generator` [...](../jlesson/cli.py#L153)

### `jlesson.asset_compiler` [...](../jlesson/asset_compiler.py#L1)

- `jlesson.language_config` [...](../jlesson/asset_compiler.py#L20)
- `jlesson.models` [...](../jlesson/asset_compiler.py#L23)
- `jlesson.profiles` [...](../jlesson/asset_compiler.py#L28)
- `jlesson.video.cards` [...](../jlesson/asset_compiler.py#L21)
- `jlesson.video.tts_engine` [...](../jlesson/asset_compiler.py#L213)

### `jlesson.language_config` [...](../jlesson/language_config.py#L1)

- `jlesson.curriculum` [...](../jlesson/language_config.py#L166)
- `jlesson.item_generator` [...](../jlesson/language_config.py#L172)
- `jlesson.models` [...](../jlesson/language_config.py#L170)
- `jlesson.prompt_template` [...](../jlesson/language_config.py#L171)
- `jlesson.video.tts_engine` [...](../jlesson/language_config.py#L26)

### `jlesson.lesson_pipeline.persist_content` [...](../jlesson/lesson_pipeline/persist_content.py#L1)

- `jlesson.lesson_pipeline.pipeline_core` [...](../jlesson/lesson_pipeline/persist_content.py#L6)
- `jlesson.lesson_pipeline.pipeline_grammar` [...](../jlesson/lesson_pipeline/persist_content.py#L7)
- `jlesson.lesson_pipeline.pipeline_paths` [...](../jlesson/lesson_pipeline/persist_content.py#L8)
- `jlesson.lesson_store` [...](../jlesson/lesson_pipeline/persist_content.py#L9)
- `jlesson.models` [...](../jlesson/lesson_pipeline/persist_content.py#L5)

### `jlesson.lesson_pipeline.compile_assets` [...](../jlesson/lesson_pipeline/compile_assets.py#L1)

- `jlesson.asset_compiler` [...](../jlesson/lesson_pipeline/compile_assets.py#L3)
- `jlesson.lesson_pipeline.pipeline_core` [...](../jlesson/lesson_pipeline/compile_assets.py#L5)
- `jlesson.lesson_pipeline.pipeline_paths` [...](../jlesson/lesson_pipeline/compile_assets.py#L6)
- `jlesson.models` [...](../jlesson/lesson_pipeline/compile_assets.py#L4)
- `jlesson.profiles` [...](../jlesson/lesson_pipeline/compile_assets.py#L7)

### `jlesson.lesson_pipeline.pipeline_core` [...](../jlesson/lesson_pipeline/pipeline_core.py#L1)

- `jlesson.language_config` [...](../jlesson/lesson_pipeline/pipeline_core.py#L7)
- `jlesson.lesson_report` [...](../jlesson/lesson_pipeline/pipeline_core.py#L8)
- `jlesson.models` [...](../jlesson/lesson_pipeline/pipeline_core.py#L9)
- `jlesson.retrieval` [...](../jlesson/lesson_pipeline/pipeline_core.py#L10)

### `jlesson.lesson_pipeline.generate_sentences` [...](../jlesson/lesson_pipeline/generate_sentences.py#L1)

- `jlesson.lesson_pipeline.pipeline_core` [...](../jlesson/lesson_pipeline/generate_sentences.py#L4)
- `jlesson.lesson_pipeline.pipeline_grammar` [...](../jlesson/lesson_pipeline/generate_sentences.py#L5)
- `jlesson.lesson_pipeline.pipeline_llm` [...](../jlesson/lesson_pipeline/generate_sentences.py#L6)
- `jlesson.models` [...](../jlesson/lesson_pipeline/generate_sentences.py#L3)

### `jlesson.lesson_pipeline` [...](../jlesson/lesson_pipeline/__init__.py#L1)

- `jlesson.curriculum` [...](../jlesson/lesson_pipeline/__init__.py#L80)
- `jlesson.lesson_pipeline.pipeline_core`
- `jlesson.lesson_pipeline.pipeline_existing_lesson`
- `jlesson.lesson_pipeline.pipeline_orchestrator`
