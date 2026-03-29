# Step: `narrative_grammar`

**File:** `jlesson/lesson_pipeline/generate_sentences/`  
**Class:** `NarrativeGrammarStep` (alias: `GenerateSentencesStep`)  
**Pipeline position:** Step 7 (after grammar selection, before sentence review)

---

## Use case

Generates Phase 3 grammar practice sentences for each lesson block.  Each block's
sentences use:
- the block-specific noun and verb subset (chunked from the full lesson vocab)
- the block-specific grammar rule(s) selected by `GrammarSelectStep`
- the block's narrative passage as situational context

The output is a flat `list[Sentence]` where every item carries `block_index` and
`phase = Phase.GRAMMAR`.  Downstream steps (`ReviewSentencesStep`, `CompileAssetsStep`)
consume these without needing to know which block they came from.

---

## Input

All inputs come from `LessonContext`:

| Field | Type | Set by |
|---|---|---|
| `ctx.nouns` | `list[GeneralItem]` | `SelectVocabStep` or `RetrieveLessonMaterialStep` |
| `ctx.verbs` | `list[GeneralItem]` | same as above |
| `ctx.narrative_blocks` | `list[str]` | `NarrativeGeneratorStep` |
| `ctx.selected_grammar_blocks` | `list[list[GrammarItem]]` | `GrammarSelectStep` |
| `ctx.selected_grammar` | `list[GrammarItem]` | `GrammarSelectStep` (flat fallback) |
| `config.num_nouns` | `int` | `LessonConfig` — nouns per block (chunk size) |
| `config.num_verbs` | `int` | `LessonConfig` — verbs per block (chunk size) |
| `config.sentences_per_grammar` | `int` | `LessonConfig` — sentences per grammar point |
| `config.lesson_blocks` | `int` | `LessonConfig` — total block count |

### Idempotency

If `ctx.sentences` is already populated (e.g. from retrieval), the step returns
immediately without any LLM call.

---

## Chunking

The step calls `_chunk(items, size) -> list[list[GeneralItem]]` to split the flat
noun/verb lists into per-block sub-lists.

| Input list | Chunk size | Example (4 nouns, 2 per block → 2 blocks) |
|---|---|---|
| `ctx.nouns` | `config.num_nouns` | `[[cat, dog], [rice, water]]` |
| `ctx.verbs` | `config.num_verbs` | `[[eat, run], [drink, sleep]]` |

`total_blocks = max(len(noun_blocks), len(verb_blocks), len(narrative_blocks), lesson_blocks)`
— the step always covers the widest dimension, using empty lists when a shorter
dimension runs out.

---

## LLM call characteristics

- **One call per block** — `total_blocks` requests in sequence.
- **Grammar routing** — `selected_grammar_blocks[i]` is used when present and
  non-empty; falls back to the flat `selected_grammar` list for that block.
- **Narrative injection** — the block's story passage is forwarded to the prompt as
  optional narrative context; the LLM keeps sentences thematically consistent.

---

## Decision paths

```
sentences already populated?
    └─ YES → return early (retrieval hit)

for each block index in range(total_blocks):
    block_nouns  = noun_blocks[i]  or []
    block_verbs  = verb_blocks[i]  or []
    block_narrative = narrative_blocks[i] or ""
    block_grammar   = selected_grammar_blocks[i] if non-empty else selected_grammar

    prompt  = build_grammar_sentences_prompt(grammar, nouns, verbs, **step_config)
    result  = PipelineRuntime.ask_llm(ctx, prompt)
    for each sentence dict in result["sentences"]:
        sentence = generator.convert_sentence(sentence_dict)
        sentence.block_index = i + 1
        sentence.phase = Phase.GRAMMAR
        ctx.sentences.append(sentence)

if sentences produced:
    ctx.report.add("grammar_practice", _grammar_section(...))
```

---

## Output

| Context field | Type | Notes |
|---|---|---|
| `ctx.sentences` | `list[Sentence]` | All blocks combined; each item has `block_index` |
| `ctx.report` | `ReportBuilder` | `## Phase 3 - Grammar Practice` section appended |

---

## Step-local types

### `NarrativeGrammarLanguageConfig`

Defined in `config.py`. Built once per step execution from the broader `LanguageConfig`.

| Field | Type | Purpose |
|---|---|---|
| `persons` | `tuple[tuple[str,str,str], ...]` | From `LanguageConfig.persons` — (native, target, phonetic) |
| `teacher_description` | `str` | LLM system framing line |
| `output_source_field` | `str` | JSON key for source-language sentence (matches `convert_sentence`) |
| `output_target_field` | `str` | JSON key for target-language sentence |
| `output_phonetic_field` | `str` | JSON key for phonetic annotation (empty = omit) |

Per-pair defaults:

| Language pair | `output_source_field` | `output_target_field` | `output_phonetic_field` |
|---|---|---|---|
| `eng-jap` | `english` | `japanese` | `romaji` |
| `hun-eng` | `hungarian` | `english` | `pronunciation` |

The output field names **must match** what `ItemGenerator.convert_sentence` reads.
`EngJapItemGenerator.convert_sentence` reads `llm_item["english"]`, `llm_item["japanese"]`,
`llm_item["romaji"]`. The step config makes this coupling explicit and testable.

---

## Prompt template

`prompt.py` contains two language-agnostic helpers:

### `format_vocab_items(items: list[GeneralItem]) -> str`

Formats a GeneralItem list using only generic fields:
- `item.source.display_text` — source display
- `item.target.display_text` — target display
- `item.target.pronunciation` — phonetic (if set)
- `item.target.extra` — notable keys (`kanji`, `masu_form`, `type`, `past_tense`)

Works for any language pair without language-specific keys.

### `build_grammar_sentences_prompt(...) -> str`

Constructs the full LLM prompt from pre-typed `GeneralItem` and `GrammarItem` objects.
Output JSON field names come from the step config, not from any language adapter.
The prompt is therefore fully testable without a `LanguageConfig` or `PromptInterface`.

---

## Runtime service

`PipelineRuntime.ask_llm(ctx, prompt)` is used for all LLM calls (not `PipelineGadgets`).
This step is fully migrated to the runtime service pattern.
