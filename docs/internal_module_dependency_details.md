# Internal Module Dependency Details: jlesson

- Backend: `grimp`
- Modules: `39`
- Internal edges: `107`
- Cycle components: `0`

## Cycle Paths

- None

## Focused Boundaries

### `lesson_pipeline` <-> `video`

- Direct imports `lesson_pipeline` -> `video`: `2`
  - `jlesson.lesson_pipeline.pipeline_orchestrator` -> `jlesson.video.builder` [...](../jlesson/lesson_pipeline/pipeline_orchestrator.py#L15)
  - `jlesson.lesson_pipeline.render_video` -> `jlesson.video.builder` [...](../jlesson/lesson_pipeline/render_video.py#L3)
- Direct imports `video` -> `lesson_pipeline`: `0`
- Cycle nodes spanning both groups: `0`
- Cycle path `lesson_pipeline` -> `video`: none
- Cycle path `video` -> `lesson_pipeline`: none

### `lesson_pipeline` <-> `asset_compiler`

- Direct imports `lesson_pipeline` -> `asset_compiler`: `2`
  - `jlesson.lesson_pipeline.compile_assets` -> `jlesson.asset_compiler` [...](../jlesson/lesson_pipeline/compile_assets.py#L3)
  - `jlesson.lesson_pipeline.pipeline_orchestrator` -> `jlesson.asset_compiler` [...](../jlesson/lesson_pipeline/pipeline_orchestrator.py#L7)
- Direct imports `asset_compiler` -> `lesson_pipeline`: `0`
- Cycle nodes spanning both groups: `0`
- Cycle path `lesson_pipeline` -> `asset_compiler`: none
- Cycle path `asset_compiler` -> `lesson_pipeline`: none


## Top Transitive Dependency Paths

### `jlesson.lesson_pipeline` [...](../jlesson/lesson_pipeline/__init__.py#L1)

- `jlesson.lesson_pipeline` -> `jlesson.lesson_pipeline.pipeline_core` -> `jlesson.language_config` -> `jlesson.prompt_template` [...](../jlesson/lesson_pipeline/__init__.py#L1)
- `jlesson.lesson_pipeline` -> `jlesson.lesson_pipeline.pipeline_gadgets` -> `jlesson.llm_client` -> `jlesson.config` [...](../jlesson/lesson_pipeline/__init__.py#L1)
- `jlesson.lesson_pipeline` -> `jlesson.lesson_pipeline.compile_assets` -> `jlesson.asset_compiler` -> `jlesson.video.tts_engine` [...](../jlesson/lesson_pipeline/__init__.py#L1)

### `jlesson.lesson_pipeline.pipeline_orchestrator` [...](../jlesson/lesson_pipeline/pipeline_orchestrator.py#L1)

- `jlesson.lesson_pipeline.pipeline_orchestrator` -> `jlesson.lesson_pipeline.pipeline_gadgets` -> `jlesson.llm_client` -> `jlesson.config` [...](../jlesson/lesson_pipeline/pipeline_orchestrator.py#L12)
- `jlesson.lesson_pipeline.pipeline_orchestrator` -> `jlesson.language_config` -> `jlesson.curriculum` [...](../jlesson/lesson_pipeline/pipeline_orchestrator.py#L8)
- `jlesson.lesson_pipeline.pipeline_orchestrator` -> `jlesson.lesson_pipeline.pipeline_gadgets` -> `jlesson.llm_client` [...](../jlesson/lesson_pipeline/pipeline_orchestrator.py#L12)

### `jlesson.cli` [...](../jlesson/cli.py#L1)

- `jlesson.cli` -> `jlesson.lesson_pipeline` -> `jlesson.lesson_pipeline.compile_assets` -> `jlesson.asset_compiler` -> `jlesson.video.cards` [...](../jlesson/cli.py#L348)
- `jlesson.cli` -> `jlesson.lesson_pipeline` -> `jlesson.lesson_pipeline.compile_assets` -> `jlesson.profiles` [...](../jlesson/cli.py#L348)
- `jlesson.cli` -> `jlesson.lesson_pipeline` -> `jlesson.lesson_pipeline.compile_touches` -> `jlesson.touch_compiler` [...](../jlesson/cli.py#L348)

### `jlesson.lesson_pipeline.save_report` [...](../jlesson/lesson_pipeline/save_report.py#L1)

- `jlesson.lesson_pipeline.save_report` -> `jlesson.lesson_pipeline.pipeline_core` -> `jlesson.language_config` -> `jlesson.curriculum` [...](../jlesson/lesson_pipeline/save_report.py#L4)
- `jlesson.lesson_pipeline.save_report` -> `jlesson.lesson_pipeline.pipeline_core` -> `jlesson.language_config` -> `jlesson.prompt_template` [...](../jlesson/lesson_pipeline/save_report.py#L4)
- `jlesson.lesson_pipeline.save_report` -> `jlesson.lesson_pipeline.pipeline_gadgets` -> `jlesson.llm_client` -> `jlesson.config` [...](../jlesson/lesson_pipeline/save_report.py#L5)

## Direct Imports For Highest Fan-Out Modules

### `jlesson.lesson_pipeline` [...](../jlesson/lesson_pipeline/__init__.py#L1)

- `jlesson.curriculum` [...](../jlesson/lesson_pipeline/__init__.py#L39)
- `jlesson.lesson_pipeline.compile_assets`
- `jlesson.lesson_pipeline.compile_touches`
- `jlesson.lesson_pipeline.generate_sentences`
- `jlesson.lesson_pipeline.grammar_select`
- `jlesson.lesson_pipeline.noun_practice`
- `jlesson.lesson_pipeline.persist_content`
- `jlesson.lesson_pipeline.pipeline_core`
- `jlesson.lesson_pipeline.pipeline_gadgets`
- `jlesson.lesson_pipeline.pipeline_orchestrator`
- `jlesson.lesson_pipeline.register_lesson`
- `jlesson.lesson_pipeline.render_video`
- `jlesson.lesson_pipeline.retrieve_material`
- `jlesson.lesson_pipeline.review_sentences`
- `jlesson.lesson_pipeline.save_report`
- `jlesson.lesson_pipeline.select_vocab`
- `jlesson.lesson_pipeline.verb_practice`

### `jlesson.lesson_pipeline.pipeline_orchestrator` [...](../jlesson/lesson_pipeline/pipeline_orchestrator.py#L1)

- `jlesson.asset_compiler` [...](../jlesson/lesson_pipeline/pipeline_orchestrator.py#L7)
- `jlesson.language_config` [...](../jlesson/lesson_pipeline/pipeline_orchestrator.py#L8)
- `jlesson.lesson_pipeline.pipeline_core` [...](../jlesson/lesson_pipeline/pipeline_orchestrator.py#L11)
- `jlesson.lesson_pipeline.pipeline_gadgets` [...](../jlesson/lesson_pipeline/pipeline_orchestrator.py#L12)
- `jlesson.lesson_store` [...](../jlesson/lesson_pipeline/pipeline_orchestrator.py#L9)
- `jlesson.models` [...](../jlesson/lesson_pipeline/pipeline_orchestrator.py#L10)
- `jlesson.profiles` [...](../jlesson/lesson_pipeline/pipeline_orchestrator.py#L13)
- `jlesson.touch_compiler` [...](../jlesson/lesson_pipeline/pipeline_orchestrator.py#L14)
- `jlesson.video.builder` [...](../jlesson/lesson_pipeline/pipeline_orchestrator.py#L15)

### `jlesson.cli` [...](../jlesson/cli.py#L1)

- `jlesson.config` [...](../jlesson/cli.py#L56)
- `jlesson.curriculum` [...](../jlesson/cli.py#L21)
- `jlesson.language_config` [...](../jlesson/cli.py#L23)
- `jlesson.lesson_pipeline` [...](../jlesson/cli.py#L348)
- `jlesson.prompt_template` [...](../jlesson/cli.py#L24)
- `jlesson.vocab_generator` [...](../jlesson/cli.py#L153)

### `jlesson.lesson_pipeline.save_report` [...](../jlesson/lesson_pipeline/save_report.py#L1)

- `jlesson.lesson_pipeline.pipeline_core` [...](../jlesson/lesson_pipeline/save_report.py#L4)
- `jlesson.lesson_pipeline.pipeline_gadgets` [...](../jlesson/lesson_pipeline/save_report.py#L5)
- `jlesson.lesson_report` [...](../jlesson/lesson_pipeline/save_report.py#L3)
- `jlesson.models` [...](../jlesson/lesson_pipeline/save_report.py#L9)
- `jlesson.profiles` [...](../jlesson/lesson_pipeline/save_report.py#L6)
- `jlesson.touch_compiler` [...](../jlesson/lesson_pipeline/save_report.py#L7)

### `jlesson.language_config` [...](../jlesson/language_config.py#L1)

- `jlesson.curriculum` [...](../jlesson/language_config.py#L166)
- `jlesson.item_generator` [...](../jlesson/language_config.py#L172)
- `jlesson.models` [...](../jlesson/language_config.py#L170)
- `jlesson.prompt_template` [...](../jlesson/language_config.py#L171)
- `jlesson.video.tts_engine` [...](../jlesson/language_config.py#L26)

### `jlesson.asset_compiler` [...](../jlesson/asset_compiler.py#L1)

- `jlesson.language_config` [...](../jlesson/asset_compiler.py#L20)
- `jlesson.models` [...](../jlesson/asset_compiler.py#L23)
- `jlesson.profiles` [...](../jlesson/asset_compiler.py#L28)
- `jlesson.video.cards` [...](../jlesson/asset_compiler.py#L21)
- `jlesson.video.tts_engine` [...](../jlesson/asset_compiler.py#L213)

### `jlesson.lesson_pipeline.compile_assets` [...](../jlesson/lesson_pipeline/compile_assets.py#L1)

- `jlesson.asset_compiler` [...](../jlesson/lesson_pipeline/compile_assets.py#L3)
- `jlesson.lesson_pipeline.pipeline_core` [...](../jlesson/lesson_pipeline/compile_assets.py#L5)
- `jlesson.lesson_pipeline.pipeline_gadgets` [...](../jlesson/lesson_pipeline/compile_assets.py#L6)
- `jlesson.models` [...](../jlesson/lesson_pipeline/compile_assets.py#L4)
- `jlesson.profiles` [...](../jlesson/lesson_pipeline/compile_assets.py#L7)

### `jlesson.lesson_pipeline.pipeline_gadgets` [...](../jlesson/lesson_pipeline/pipeline_gadgets.py#L1)

- `jlesson.language_config` [...](../jlesson/lesson_pipeline/pipeline_gadgets.py#L6)
- `jlesson.llm_cache` [...](../jlesson/lesson_pipeline/pipeline_gadgets.py#L38)
- `jlesson.llm_client` [...](../jlesson/lesson_pipeline/pipeline_gadgets.py#L7)
- `jlesson.models` [...](../jlesson/lesson_pipeline/pipeline_gadgets.py#L8)
- `jlesson.vocab_generator` [...](../jlesson/lesson_pipeline/pipeline_gadgets.py#L25)

### `jlesson.lesson_pipeline.persist_content` [...](../jlesson/lesson_pipeline/persist_content.py#L1)

- `jlesson.lesson_pipeline.pipeline_core` [...](../jlesson/lesson_pipeline/persist_content.py#L6)
- `jlesson.lesson_pipeline.pipeline_gadgets` [...](../jlesson/lesson_pipeline/persist_content.py#L7)
- `jlesson.lesson_store` [...](../jlesson/lesson_pipeline/persist_content.py#L8)
- `jlesson.models` [...](../jlesson/lesson_pipeline/persist_content.py#L5)

### `jlesson.lesson_pipeline.pipeline_core` [...](../jlesson/lesson_pipeline/pipeline_core.py#L1)

- `jlesson.language_config` [...](../jlesson/lesson_pipeline/pipeline_core.py#L7)
- `jlesson.lesson_report` [...](../jlesson/lesson_pipeline/pipeline_core.py#L8)
- `jlesson.models` [...](../jlesson/lesson_pipeline/pipeline_core.py#L9)
- `jlesson.retrieval` [...](../jlesson/lesson_pipeline/pipeline_core.py#L10)
