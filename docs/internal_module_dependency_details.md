# Internal Module Dependency Details: jlesson

- Backend: `grimp`
- Modules: `39`
- Internal edges: `109`
- Cycle components: `1`

## Cycle Paths

- `jlesson.asset_compiler -> jlesson.lesson_pipeline -> jlesson.lesson_pipeline.compile_assets -> jlesson.asset_compiler`

## Top Transitive Dependency Paths

### `jlesson.lesson_pipeline`

- `jlesson.lesson_pipeline -> jlesson.lesson_pipeline.pipeline_core -> jlesson.language_config -> jlesson.prompt_template`
- `jlesson.lesson_pipeline -> jlesson.lesson_pipeline.pipeline_gadgets -> jlesson.llm_client -> jlesson.config`
- `jlesson.lesson_pipeline -> jlesson.lesson_pipeline.compile_assets -> jlesson.asset_compiler -> jlesson.video.tts_engine`

### `jlesson.lesson_pipeline.pipeline_orchestrator`

- `jlesson.lesson_pipeline.pipeline_orchestrator -> jlesson.lesson_pipeline.pipeline_gadgets -> jlesson.llm_client -> jlesson.config`
- `jlesson.lesson_pipeline.pipeline_orchestrator -> jlesson.asset_compiler -> jlesson.lesson_pipeline -> jlesson.lesson_pipeline.compile_assets`
- `jlesson.lesson_pipeline.pipeline_orchestrator -> jlesson.asset_compiler -> jlesson.lesson_pipeline -> jlesson.lesson_pipeline.compile_touches`

### `jlesson.asset_compiler`

- `jlesson.asset_compiler -> jlesson.lesson_pipeline -> jlesson.lesson_pipeline.pipeline_gadgets -> jlesson.llm_client -> jlesson.config`
- `jlesson.asset_compiler -> jlesson.lesson_pipeline -> jlesson.lesson_pipeline.pipeline_gadgets -> jlesson.llm_client`
- `jlesson.asset_compiler -> jlesson.lesson_pipeline -> jlesson.lesson_pipeline.compile_touches -> jlesson.touch_compiler`

### `jlesson.cli`

- `jlesson.cli -> jlesson.lesson_pipeline -> jlesson.lesson_pipeline.compile_assets -> jlesson.asset_compiler -> jlesson.video.cards`
- `jlesson.cli -> jlesson.lesson_pipeline -> jlesson.lesson_pipeline.compile_assets -> jlesson.profiles`
- `jlesson.cli -> jlesson.lesson_pipeline -> jlesson.lesson_pipeline.compile_touches -> jlesson.touch_compiler`

### `jlesson.lesson_pipeline.save_report`

- `jlesson.lesson_pipeline.save_report -> jlesson.lesson_pipeline.pipeline_core -> jlesson.language_config -> jlesson.curriculum`
- `jlesson.lesson_pipeline.save_report -> jlesson.lesson_pipeline.pipeline_core -> jlesson.language_config -> jlesson.prompt_template`
- `jlesson.lesson_pipeline.save_report -> jlesson.lesson_pipeline.pipeline_gadgets -> jlesson.llm_client -> jlesson.config`

## Direct Imports For Highest Fan-Out Modules

### `jlesson.lesson_pipeline`

- `jlesson.curriculum`
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

### `jlesson.lesson_pipeline.pipeline_orchestrator`

- `jlesson.asset_compiler`
- `jlesson.language_config`
- `jlesson.lesson_pipeline.pipeline_core`
- `jlesson.lesson_pipeline.pipeline_gadgets`
- `jlesson.lesson_store`
- `jlesson.models`
- `jlesson.profiles`
- `jlesson.touch_compiler`
- `jlesson.video.builder`

### `jlesson.asset_compiler`

- `jlesson.language_config`
- `jlesson.lesson_pipeline`
- `jlesson.models`
- `jlesson.profiles`
- `jlesson.video.cards`
- `jlesson.video.tts_engine`

### `jlesson.cli`

- `jlesson.config`
- `jlesson.curriculum`
- `jlesson.language_config`
- `jlesson.lesson_pipeline`
- `jlesson.prompt_template`
- `jlesson.vocab_generator`

### `jlesson.lesson_pipeline.save_report`

- `jlesson.lesson_pipeline.pipeline_core`
- `jlesson.lesson_pipeline.pipeline_gadgets`
- `jlesson.lesson_report`
- `jlesson.models`
- `jlesson.profiles`
- `jlesson.touch_compiler`

### `jlesson.lesson_pipeline.pipeline_gadgets`

- `jlesson.language_config`
- `jlesson.llm_cache`
- `jlesson.llm_client`
- `jlesson.models`
- `jlesson.vocab_generator`

### `jlesson.lesson_pipeline.compile_assets`

- `jlesson.asset_compiler`
- `jlesson.lesson_pipeline.pipeline_core`
- `jlesson.lesson_pipeline.pipeline_gadgets`
- `jlesson.models`
- `jlesson.profiles`

### `jlesson.language_config`

- `jlesson.curriculum`
- `jlesson.item_generator`
- `jlesson.models`
- `jlesson.prompt_template`
- `jlesson.video.tts_engine`

### `jlesson.lesson_pipeline.persist_content`

- `jlesson.lesson_pipeline.pipeline_core`
- `jlesson.lesson_pipeline.pipeline_gadgets`
- `jlesson.lesson_store`
- `jlesson.models`

### `jlesson.lesson_pipeline.pipeline_core`

- `jlesson.language_config`
- `jlesson.lesson_report`
- `jlesson.models`
- `jlesson.retrieval`
