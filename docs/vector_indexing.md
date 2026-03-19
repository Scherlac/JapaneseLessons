
# Feature Request: Unified Lesson Material Database with Multilingual Branching

Status: Proposed  
Date: 2026-03-19  
Priority: High  
Complexity: 21

## Summary

Create a lesson material database where English is the canonical system language, embeddings are the primary index, and flexible metadata tags are the secondary index for filtering and boosting. Additional languages are attached to canonical nodes as branches in the same concept graph.

## Problem

Current lesson material generation and retrieval are content-centric but not yet organized around a unified multilingual knowledge structure. This causes three issues:

1. Concept lookup is weak across language boundaries.
2. Content expansion for new languages risks duplication and semantic drift.
3. Semantic search cannot reliably map equivalent concepts between languages.

## Goals

1. Use English as the canonical content backbone.
2. Make vector search the primary retrieval mechanism.
3. Use extensible metadata tags as secondary filtering, routing, and reranking controls.
4. Attach every additional language as branch content under shared canonical nodes.
5. Support lesson generation workflows using this shared semantic structure.

## Non-Goals

1. Building a full translation management platform.
2. Replacing existing curriculum progression logic in this phase.
3. Adding all languages immediately; design should support gradual rollout.
4. Defining a new LLM provider strategy.

## Core Design

### Canonical Model

1. Canonical node language is English.
2. Each node represents one lesson concept unit (noun, verb, phrase, grammar example, or narrative fragment).
3. Node stores:
- canonical_text_en
- concept_type
- embedding_vector
- metadata (theme, level, tags, usage)

### Multilingual Branch Model

1. Additional language content is attached to canonical nodes.
2. Each branch stores:
- language_code
- localized_text
- pronunciation or phonetics
- notes, usage examples, and optional cultural context
3. Branches inherit canonical node identity and retrieval lineage.

### Vector + Flexible Metadata Index

1. Primary index:
- nearest-neighbor vector search over canonical English embeddings
2. Secondary index:
- metadata filters and boosts (schema-extensible)
- examples: theme, difficulty, concept_type, language availability
- optional language-specific grammar progression keys, for example `grammar_progression.ja=beginner.l1.s2`
3. Query flow:
- embed query
- retrieve top-k canonical candidates from vector index
- apply metadata filters/boosts/reranking
- resolve best canonical node set
- project requested language branch payload

## Functional Requirements

1. Ingest English lesson material into canonical nodes.
2. Generate and store embeddings for canonical content.
3. Attach multilingual branches to existing canonical nodes.
4. Retrieve by:
- semantic similarity
- metadata tags (theme, level, language, grammar progression)
5. Return aligned multilingual payload for lesson generation.

## Data Integrity Rules

1. No branch may exist without a canonical English node.
2. Canonical node ID is globally stable.
3. Branch updates must not mutate canonical meaning fields.
4. Embedding refresh must be versioned.
5. Duplicate concept detection should run during ingest.

## Metadata Strategy

1. Core tags:
- theme
- level
- concept_type
2. Language tags:
- language_code
- branch_quality
3. Grammar progression tags:
- language-scoped keys, for example:
	- `grammar_progression.ja=beginner.l1.s2`
	- `grammar_progression.hu_eng=present_simple_affirmative`
4. Governance:
- tag namespaces should be documented and versioned to avoid uncontrolled growth.

## API/Workflow Expectations

1. Upsert canonical node.
2. Upsert branch for node and language.
3. Search semantic index with optional metadata constraints.
4. Fetch full node package for lesson assembly.
5. Batch operations for large vocabulary/theme onboarding.

## Acceptance Criteria

1. English canonical content can be ingested and indexed end-to-end.
2. At least one non-English branch language can be linked and retrieved with canonical alignment.
3. Semantic search returns relevant canonical nodes with branch payload in under target latency.
4. Metadata filtering by language-specific grammar progression key works correctly.
5. Lesson generation pipeline can consume retrieval output without schema mismatch.

## Rollout Plan

### Phase 1: Foundation

1. Define canonical and branch schemas.
2. Implement canonical ingest and embedding generation.
3. Define metadata taxonomy and namespace conventions.

### Phase 2: Multilingual Branching

1. Implement branch attachment and validation.
2. Add language-aware retrieval response format.
3. Add consistency checks for branch-to-node mapping.

### Phase 3: Retrieval Intelligence

1. Add metadata filtering and boosting on top of vector retrieval.
2. Add grammar progression key support for language-specific queries.
3. Add quality metrics for retrieval relevance and branch coverage.

### Phase 4: Integration

1. Integrate retrieval into lesson content generation.
2. Add operational tooling for reindex and embedding version migration.

## Risks

1. Semantic drift between canonical meaning and branch translations.
2. Embedding model changes causing retrieval inconsistency.
3. Metadata sprawl and inconsistent tag usage.
4. Increased maintenance cost as languages scale.

## Mitigations

1. Enforce branch review and meaning-alignment checks.
2. Version embeddings and support reindex pipelines.
3. Define metadata namespace governance and validation rules.
4. Add automated coverage and consistency reports.

## Success Metrics

1. Retrieval precision at top-k for lesson material queries.
2. Branch coverage ratio by language.
3. Canonical-to-branch alignment error rate.
4. Lesson generation reuse rate from indexed materials.
5. End-to-end retrieval latency percentile targets.

## Open Questions

1. Should embeddings be generated from canonical text only, or canonical plus selected metadata?
2. How strict should branch approval be before branch content becomes production-eligible?
3. What is the minimum branch completeness threshold for enabling a new language in lesson generation?
4. Should narrative fragments be first-class nodes or attached as metadata to concept nodes?



## User Stories

1. As a curriculum author, I want to search by semantic meaning in English and receive aligned Japanese and Hungarian branches, so I can assemble coherent multilingual lesson material quickly.
2. As a lesson generator, I want metadata filtering by level, theme, and grammar progression key, so I can retrieve content that matches lesson constraints without manual curation.
3. As a language maintainer, I want to attach new language branches to existing canonical nodes, so I can expand language coverage without duplicating concept IDs.
4. As an evaluator, I want retrieval quality metrics per language branch, so I can detect semantic drift and branch quality regressions early.
5. As a platform engineer, I want embedding versioning and reindex tooling, so model upgrades do not break retrieval consistency.

## Spike Implementations

### Spike 1: Baseline Vector Retrieval

Goal:
- Validate vector-only retrieval on canonical English nodes.

Scope:
- Ingest 200 to 500 canonical nodes.
- Generate embeddings using one API model.
- Run top-k semantic search benchmark set.

Success Criteria:
- Stable top-k relevance for core lesson queries.
- P95 retrieval latency under agreed threshold.

### Spike 2: Vector + Metadata Filtering

Goal:
- Validate secondary metadata constraints without harming semantic quality.

Scope:
- Add metadata tags: theme, level, concept_type.
- Add grammar progression key examples for Japanese.
- Compare retrieval quality with and without metadata filters.

Success Criteria:
- Filtered results preserve semantic relevance.
- Metadata constraints reduce off-topic candidates.

### Spike 3: Multilingual Branch Projection

Goal:
- Validate canonical-to-branch projection quality.

Scope:
- Add Japanese and one additional language branch to shared canonical nodes.
- Query in English and project branch payload.
- Check branch completeness and alignment.

Success Criteria:
- Branch payload maps correctly to canonical IDs.
- Low alignment error rate across sampled nodes.

### Spike 4: Embedding Payload Strategy

Goal:
- Compare canonical-text-only embeddings vs canonical plus selected metadata embeddings.

Scope:
- Build two embedding datasets over same node set.
- Run identical query benchmark on both.
- Track precision at k, latency, and maintenance overhead.

Success Criteria:
- Clear recommendation for production default.
- Decision captured with measurable trade-offs.

## Spike Execution Plan

1. Run spikes sequentially in the listed order.
2. Use one fixed benchmark query set across all spikes.
3. Record model name, version, and indexing parameters for reproducibility.
4. Store results in docs/development_history.md and promote final choices into this document.

## Complexity Note

Complexity remains 21.

Interpretation:
- Medium-high research and integration complexity.
- Manageable through phased spikes before full implementation.