---
status: Active
source_of_truth: Yes
last_updated: 2026-04-13
superseded_by: N/A
---

# Fork Boundary Matrix

## Purpose

This document locks the Phase 0 / Phase 1 boundary for thin-fork realignment work.

It answers two questions:

1. What current little-crab behavior must be preserved while restructuring?
2. Which parts of the codebase should be reused directly, reused behind an adapter, or remain fork-specific?

## Preserve Set

The following behavior is treated as locked unless an explicit architecture decision changes it:

- local-first runtime remains the default and required operating mode
- canonical runtime topology remains:
  - Ladybug graph
  - DuckDB documents/registry/policy/analysis
  - embedded Chroma vector index
- current CLI command surface remains available:
  - `littlecrab`
  - `ltcrab`
  - `little-crab`
  - `opencrab` (deprecated compatibility)
- current MCP tool naming remains aligned with OpenCrab compatibility
- OpenCrab grammar and validator semantics remain preserved
- read-only agent context remains derived and non-canonical
- current staged-write workflow remains preserved
- current local-only identity remains preserved

## Boundary Categories

### Category A — Direct reuse preferred

These areas should stay as close to upstream OpenCrab as practical.

- `opencrab/grammar/*`
- grammar manifest and validator behavior
- ontology-level semantics when backend assumptions are absent
- MCP protocol compatibility expectations
- tool naming compatibility

### Category B — Reuse behind an adapter boundary

These areas are shared enough to follow upstream direction, but local-first runtime differences should be pushed downward.

- `opencrab/cli.py`
- `opencrab/mcp/tools.py`
- `opencrab/config.py`
- `opencrab/ontology/query.py`
- `opencrab/ontology/context_pipeline.py`
- `opencrab/ontology/extractor.py`

Rule:

- keep these files thin
- move local-only branching into lower adapter/service/factory layers when possible

### Category C — Fork-specific by design

These areas represent the local backend/profile divergence that justifies the fork.

- `opencrab/stores/duckdb_store.py`
- `opencrab/stores/ladybug_store.py`
- local embedded Chroma wiring/profile details
- local-first store resolution in `opencrab/stores/factory.py`
- docs/intelligence/AGENTS operational overlays

Rule:

- divergence is allowed here
- but upper ontology/runtime layers should only depend on stable contracts

## High-Conflict Coordinator Files

These files should be thinned before broader upstream catch-up work:

- `opencrab/cli.py`
- `opencrab/mcp/tools.py`
- `opencrab/config.py`
- `opencrab/stores/factory.py`

Thin target:

- routing/orchestration stays here
- backend/profile branching moves lower
- user-facing behavior remains unchanged

## Upstream Review Rubric

Every upstream delta should be classified into one of four review buckets:

### Adopt

Use when the change:

- improves shared ontology/runtime capability
- fits current preserve set
- does not widen little-crab into a different product

Typical examples:

- grammar/validator fixes
- extractor improvements
- MCP protocol compliance
- test and quality improvements

### Reinterpret

Use when the upstream direction is useful but the implementation assumes a different backend or product surface.

Typical examples:

- CLI/runtime wiring changes
- query/runtime improvements tied to a different local backend
- transport abstractions that should stay local-only for now

### Defer

Use when the change is strategically interesting but not needed yet.

Typical examples:

- optional remote runtime surfaces
- future operator UX/product ideas

### Reject

Use when the change would thicken the fork or redefine the product.

Typical examples:

- importing upstream web/app surfaces into core little-crab
- importing harness/orchestration product layers into core little-crab
- reintroducing service-first infrastructure without an explicit architecture decision

## Success Criteria For Thin-Fork Work

- preserve set still holds after refactors
- coordinator files become thinner over time
- more upstream logic can be reused without broad file forks
- backend divergence remains explicit instead of leaking upward
