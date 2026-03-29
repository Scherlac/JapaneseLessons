# Step: `narrative_generator`

**File:** `jlesson/lesson_pipeline/narrative_generator/`  
**Class:** `NarrativeGeneratorStep`  
**Pipeline position:** Step 3 (after vocab selection, before vocab extraction)

---

## Use case

Generates a coherent story frame that all later steps use as situational context.
Without it, sentence generation has no grounding — grammar and vocabulary exercises
would be disconnected from a shared situation.

The narrative is a list of short prose paragraphs (one per lesson block). Each block
becomes the narrative context for sentences generated in `NarrativeGrammarStep`.

---

## Input

All inputs come from `LessonContext`:

| Source | Field | Type | Notes |
|---|---|---|---|
| `LessonConfig` | `theme` | `str` | Topic for the narrative (e.g. `"a day on a farm"`) |
| `LessonConfig` | `lesson_blocks` | `int` | How many blocks to produce (default 1) |
| `LessonConfig` | `narrative` | `list[str]` | Optional pre-written blocks from CLI `--narrative` |
| `LessonContext` | `curriculum` | `CurriculumData` | Used only for lesson numbering (`len(lessons) + 1`) |
| `LessonContext` | `narrative_blocks` | `list[str]` | Pre-populated = step is skipped (idempotent) |
| `ctx.language_config` | `source.display_name` | `str` | Written into the prompt so the LLM narrates in the right language |
| `ctx.language_config` | (via registry) | `Callable` | Default fallback block builder for this language pair |

---

## Output

| Context field | Type | Notes |
|---|---|---|
| `ctx.narrative_blocks` | `list[str]` | Exactly `lesson_blocks` plain-text strings |
| `ctx.report` | `ReportBuilder` | `## Narrative Progression` section appended |

---

## LLM call characteristics

- **One call per step execution** — all blocks requested in a single JSON response.
- **No chunking** — `lesson_blocks` is typically 1–4; the full array is in one request.
- **Fallback on under-delivery** — if the LLM returns fewer blocks than requested, the
  step fills missing slots from the language-specific `default_block_builder`. A warning
  is logged when this fallback is triggered.

---

## Decision paths

```
narrative_blocks already populated?
    └─ YES → return early (idempotent, used after retrieval hit)

provided >= lesson_blocks (enough pre-written blocks from CLI)?
    └─ YES → use provided[:lesson_blocks], no LLM call

otherwise:
    1. call LLM with theme, lesson_number, block_count, seed_blocks=provided
    2. merge: start with provided, fill LLM results up to block_count
    3. if still short: fill from default_block_builder(theme, lesson_number, block_count)
    4. warn if fallback was needed
    5. truncate to block_count
```

---

## Step-local types

### `NarrativeGeneratorLanguageConfig`

Defined in `config.py`. Extracted from `LanguageConfig` once per step execution.

| Field | Type | Source |
|---|---|---|
| `source_language_label` | `str` | `language_config.source.display_name` |
| `default_block_builder` | `Callable[[str, int, int], list[str]]` | Registry in `config.py`, keyed by `language_config.code` |

The `default_block_builder` callable has signature `(theme, lesson_number, block_count) → list[str]`.
Language-specific implementations live in `config.py` (not in `ItemGenerator`).

### `build_narrative_generator_prompt`

Defined in `prompt.py`. Language-agnostic — the target language is passed as
`source_language_label`. Returns a plain-text prompt requesting a JSON response:

```json
{"blocks": [{"index": 1, "narrative": "..."}]}
```

---

## Module dependencies

```
narrative_generator/step.py
    ├── pipeline_core  (LessonContext, PipelineStep)
    ├── runtime        (PipelineRuntime.ask_llm)
    ├── .config        (build_narrative_generator_language_config)
    └── .prompt        (build_narrative_generator_prompt)

narrative_generator/config.py
    └── language_config  (LanguageConfig — read source.display_name + code only)

narrative_generator/prompt.py
    └── (no external jlesson imports)
```

This step does **not** import from `prompt_template` or touch `ctx.language_config.prompts`.

---

## Architecture alignment

This step is the reference implementation of the **step subpackage pattern**:

- Step-local `config.py` owns the language-specific wiring for this step only.
- No `PromptInterface` coupling — prompt builder is a plain function, not a method.
- `PipelineRuntime` replaces `PipelineGadgets` as the LLM gateway.
- Default block text for each language pair lives in `config.py`, not in `ItemGenerator`.

See [decision_engine_service_boundaries.md](../decision_engine_service_boundaries.md)
for the broader architecture context and the gradual migration path.

---

## Known remaining issues

| Issue | Location | Plan |
|---|---|---|
| `len(ctx.curriculum.lessons)` lesson numbering | `step.py` | Resolved by `CurriculumData` typed model |
| `ctx.narrative_vocab_terms: list[dict]` downstream | `pipeline_core.py` | Future: type as `list[NarrativeVocabBlock]` |
