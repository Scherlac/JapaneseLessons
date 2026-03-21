# Japanese Learning Material — Project Scale Topics

Status: Active reference  
Updated: 2026-03-21

---

## Purpose

This document tracks system-level topics that matter once the project grows beyond
single-feature implementation.

It is not a changelog and not a daily progress report.

Use it to answer:

1. What parts of the system are becoming long-term platforms?
2. Where will scale or complexity pressure appear next?
3. Which topics deserve architectural treatment before more features are added?

Related documents:

- Current feature focus: [../progress_report.md](../progress_report.md)
- Project history: [development_history.md](development_history.md)
- Architecture reference: [architecture.md](architecture.md)

---

## Scale Chapters

The project is now large enough to discuss growth in a few stable chapters:

1. Content and curriculum model
2. LLM generation and validation
3. Compilation and output rendering
4. Retrieval and multilingual knowledge base
5. Quality, operability, and delivery discipline

These same chapters are reused in [development_history.md](development_history.md) so
history remains detailed but easier to scan at project scale.

---

## 1. Content And Curriculum Model

### Current state

- Curriculum progression exists and is stable for the current lesson path.
- Vocabulary is theme-based JSON stored at the repository root.
- Lesson content is persisted per output lesson.

### Scale pressure

- theme files do not yet behave like a governed content corpus
- difficulty and semantic metadata are still too thin for retrieval-heavy workflows
- cross-theme duplication risk grows as more languages and themes are added

### What this chapter needs next

- canonical schema boundaries for reusable content
- stronger vocab metadata and deduplication rules
- clearer separation between source material and generated lesson instances

---

## 2. LLM Generation And Validation

### Current state

- Prompt building is modular.
- OpenAI-compatible client behavior is proven against LM Studio.
- Sentence review adds a corrective quality loop.
- LLM cache reduces repeated development cost.

### Scale pressure

- long pipelines still behave like one large transaction
- shared client configuration limits future multi-model flexibility
- quality control remains mostly prompt-driven and heuristic

### What this chapter needs next

- checkpointing between long-running stages
- retrieval-aware generation prompts
- clearer evidence capture for model, prompt, and output quality changes

---

## 3. Compilation And Output Rendering

### Current state

- assets and touches are explicitly modeled
- profiles separate repetition policy from rendering mechanics
- video and markdown report output already consume compiled touch sequences

### Scale pressure

- more output formats will increase integration surface area
- cross-platform font behavior is still under-specified
- asset reuse strategy becomes more important as lesson counts grow

### What this chapter needs next

- cross-platform font configuration
- stronger exporter boundaries for future Anki and text review modes
- repeatable artifact inspection and re-render workflows

---

## 4. Retrieval And Multilingual Knowledge Base

### Current state

- the feature is specified in [vector_indexing.md](vector_indexing.md)
- the production code does not yet have canonical-node or branch persistence
- current lesson generation is still content-generation first, retrieval second

### Scale pressure

- semantic reuse across themes and languages will not scale with flat theme files alone
- branch alignment and metadata governance become real concerns once multiple languages are attached
- embedding refreshes and reindex operations will become operational responsibilities

### What this chapter needs next

- canonical node / branch schemas
- vector index implementation strategy
- retrieval tracing and evaluation loop
- metadata namespace governance

---

## 5. Quality, Operability, And Delivery Discipline

### Current state

- the project already has strong unit-test coverage for the local path
- design decisions and spikes are documented
- the repo follows a spike-before-scale development style

### Scale pressure

- the documentation set had started to overlap and blur responsibilities
- long-running workflows need better recovery and operational visibility
- research artifacts, active work, and architectural truth need clean separation

### What this chapter needs next

- keep the three-document reporting split stable
- maintain compact architecture documentation for current truth
- continue moving completed feature detail into structured history instead of active reports

---

## Near-Term Architectural Priorities

1. Retrieval integration with safe fallback
2. Vocabulary durability and metadata hardening
3. Pipeline checkpointing for long-running lesson generation
4. Cross-platform rendering configuration

---

## Governance Rules For Documentation

1. [../progress_report.md](../progress_report.md) should describe only active development.
2. [development_history.md](development_history.md) should retain completed feature-level detail.
3. [development_history.md](development_history.md) should organize that detail by the scale chapters above.
4. [architecture.md](architecture.md) should stay compact and reflect current truth, not proposal backlog.
5. Deep rationale should live in decision documents, not in status reports.