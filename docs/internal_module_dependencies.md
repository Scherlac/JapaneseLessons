# Internal Module Dependencies: jlesson

- Backend: `grimp`
- Modules: `44`
- Internal edges: `105`
- Cycles: `0`

## Diagram

```mermaid
flowchart LR
    asset_compiler -->|2| video
    asset_compiler -->|1| models
    asset_compiler -->|1| profiles
    asset_compiler -->|1| language_config
    cli -->|1| vocab_generator
    cli -->|1| config
    cli -->|1| language_config
    cli -->|1| lesson_pipeline
    cli -->|1| prompt_template
    cli -->|1| curriculum
    curriculum -->|1| models
    item_generator -->|1| models
    language_config -->|1| item_generator
    language_config -->|1| models
    language_config -->|1| prompt_template
    language_config -->|1| video
    language_config -->|1| curriculum
    lesson_pipeline -->|10| models
    lesson_pipeline -->|4| language_config
    lesson_pipeline -->|4| curriculum
    lesson_pipeline -->|4| profiles
    lesson_pipeline -->|3| touch_compiler
    lesson_pipeline -->|2| retrieval
    lesson_pipeline -->|2| lesson_report
    lesson_pipeline -->|2| asset_compiler
    lesson_pipeline -->|2| video
    lesson_pipeline -->|2| lesson_store
    lesson_pipeline -->|1| llm_client
    lesson_pipeline -->|1| llm_cache
    lesson_pipeline -->|1| vocab_generator
    lesson_store -->|1| models
    llm_cache -->|1| llm_client
    llm_client -->|1| config
    profiles -->|1| models
    prompt_template -->|1| models
    touch_compiler -->|1| models
    touch_compiler -->|1| profiles
    video -->|1| language_config
    video -->|1| models
    vocab_generator -->|1| prompt_template
    vocab_generator -->|1| llm_client
    asset_compiler[asset_compiler]
    cli[cli]
    config[config]
    curriculum[curriculum]
    item_generator[item_generator]
    language_config[language_config]
    lesson_pipeline[lesson_pipeline]
    lesson_report[lesson_report]
    lesson_store[lesson_store]
    llm_cache[llm_cache]
    llm_client[llm_client]
    models[models]
    profiles[profiles]
    prompt_template[prompt_template]
    retrieval[retrieval]
    touch_compiler[touch_compiler]
    video[video]
    vocab_generator[vocab_generator]
```

## Highest Fan-Out

- `jlesson.lesson_pipeline.pipeline_existing_lesson`: `9` [...](../jlesson/lesson_pipeline/pipeline_existing_lesson.py#L1)
- `jlesson.cli`: `6` [...](../jlesson/cli.py#L1)
- `jlesson.lesson_pipeline.save_report`: `6` [...](../jlesson/lesson_pipeline/save_report.py#L1)
- `jlesson.lesson_pipeline.pipeline_gadgets`: `5` [...](../jlesson/lesson_pipeline/pipeline_gadgets.py#L1)
- `jlesson.lesson_pipeline.compile_assets`: `5` [...](../jlesson/lesson_pipeline/compile_assets.py#L1)
- `jlesson.lesson_pipeline.persist_content`: `5` [...](../jlesson/lesson_pipeline/persist_content.py#L1)
- `jlesson.asset_compiler`: `5` [...](../jlesson/asset_compiler.py#L1)
- `jlesson.language_config`: `5` [...](../jlesson/language_config.py#L1)
- `jlesson.lesson_pipeline.pipeline_core`: `4` [...](../jlesson/lesson_pipeline/pipeline_core.py#L1)
- `jlesson.lesson_pipeline.generate_sentences`: `4` [...](../jlesson/lesson_pipeline/generate_sentences.py#L1)

## Highest Fan-In

- `jlesson.models`: `19` [...](../jlesson/models.py#L1)
- `jlesson.lesson_pipeline.pipeline_core`: `16` [...](../jlesson/lesson_pipeline/pipeline_core.py#L1)
- `jlesson.language_config`: `7` [...](../jlesson/language_config.py#L1)
- `jlesson.lesson_pipeline.pipeline_llm`: `6` [...](../jlesson/lesson_pipeline/pipeline_llm.py#L1)
- `jlesson.curriculum`: `6` [...](../jlesson/curriculum.py#L1)
- `jlesson.lesson_pipeline.pipeline_paths`: `6` [...](../jlesson/lesson_pipeline/pipeline_paths.py#L1)
- `jlesson.lesson_pipeline.pipeline_grammar`: `6` [...](../jlesson/lesson_pipeline/pipeline_grammar.py#L1)
- `jlesson.profiles`: `6` [...](../jlesson/profiles.py#L1)
- `jlesson.llm_client`: `3` [...](../jlesson/llm_client.py#L1)
- `jlesson.touch_compiler`: `3` [...](../jlesson/touch_compiler.py#L1)

## Cross-Group Dependencies

- `asset_compiler` -> `video` (2), `models` (1), `profiles` (1), `language_config` (1)
- `cli` -> `vocab_generator` (1), `config` (1), `language_config` (1), `lesson_pipeline` (1), `prompt_template` (1), `curriculum` (1)
- `curriculum` -> `models` (1)
- `item_generator` -> `models` (1)
- `language_config` -> `item_generator` (1), `models` (1), `prompt_template` (1), `video` (1), `curriculum` (1)
- `lesson_pipeline` -> `models` (10), `language_config` (4), `curriculum` (4), `profiles` (4), `touch_compiler` (3), `retrieval` (2), `lesson_report` (2), `asset_compiler` (2), `video` (2), `lesson_store` (2), `llm_client` (1), `llm_cache` (1), `vocab_generator` (1)
- `lesson_store` -> `models` (1)
- `llm_cache` -> `llm_client` (1)
- `llm_client` -> `config` (1)
- `profiles` -> `models` (1)
- `prompt_template` -> `models` (1)
- `touch_compiler` -> `models` (1), `profiles` (1)
- `video` -> `language_config` (1), `models` (1)
- `vocab_generator` -> `prompt_template` (1), `llm_client` (1)

## Cycles

- None
