---
status: Active
source_of_truth: Yes
last_updated: 2026-04-13
superseded_by: N/A
---

# OpenCrab Upstream Catch-up Backlog

## Purpose

This backlog turns the upstream trajectory strategy into an execution queue.

It is intentionally **lane-based**, not merge-based:

- each backlog item represents an upstream capability cluster
- each item is classified using the fork-boundary rubric
- each item should be implemented or rejected independently

## Current State

Completed groundwork:

- Phase 0/1 — preserve set and fork boundary
- Phase 2 — high-conflict coordinator thinning
- Phase 3 — extractor/intelligence pilot catch-up
- Phase 4 — automation-ready extractor diagnostics

This means little-crab is now ready to begin **real upstream-lane adoption work** instead of only prep work.

## Active Lanes

### Lane A — Extractor/intelligence follow-through

- **Upstream signals**
  - `bc0466e` — extractor direction
- **Classification**
  - `Adopt` / `Reinterpret`
- **Status**
  - **Pilot complete; detailed delta inventory created**
- **What is already done**
  - local-first heuristic floor preserved
  - optional Anthropic-backed chunked enrichment added
  - diagnostics made machine-readable
- **Remaining work**
  - compare upstream extractor prompt/schema details more deeply
  - decide whether adjacent intelligence logic beyond extraction should be pulled into the same seam
  - evaluate whether provider abstraction should widen beyond Anthropic
- **Next action**
  - use `docs/EXTRACTOR_DELTA_INVENTORY.md` as the implementation guide for the next follow-through pass

### Lane B — MCP/CLI protocol compatibility catch-up

- **Upstream signals**
  - remote MCP/API transport changes
  - protocol adapter and runtime-surface changes
- **Classification**
  - `Reinterpret`
- **Status**
  - **Inventory complete; ready for a bounded follow-up patch**
- **Why it matters**
  - keeps core interfaces closer to upstream
  - improves long-term syncability without requiring hosted/server-first runtime
- **Constraints**
  - do not import remote deployment obligations into core little-crab
- **Next action**
  - use `docs/MCP_PROTOCOL_COMPATIBILITY_INVENTORY.md` to choose the next bounded protocol/diagnostics follow-up

### Lane C — Tests and quality parity

- **Upstream signals**
  - strengthened regression coverage
  - protocol/CLI/store test evolution
- **Classification**
  - `Adopt`
- **Status**
  - **Ready**
- **Why it matters**
  - reduces future merge cost
  - catches drift early
- **Next action**
  - keep the surrogate-sanitization regression test adopted and continue importing only clearly compatible parity cases

### Lane D — Automation-ready outputs and diagnostics

- **Upstream signals**
  - harness-friendly structured outputs
  - runtime observability improvements
- **Classification**
  - `Reinterpret`
- **Status**
  - **Started**
- **What is already done**
  - extractor diagnostics are now structured and machine-readable
- **Remaining work**
  - extend explicit diagnostics to more MCP/CLI paths where it helps external orchestration
- **Next action**
  - identify the next 1-2 high-value machine-readable summaries to standardize

## Deferred / Not For Core

### Lane E — Remote server surfaces

- **Upstream signals**
  - `130d9c1`
  - `1bc9e0c`
  - `6f4d0cd`
- **Classification**
  - `Defer`
- **Reason**
  - structural ideas are useful, but hosted/server-first runtime is not a current core goal

### Lane F — Web product surfaces

- **Upstream signals**
  - `8ff9ec5`
  - `f1738b8`
  - `036402f`
- **Classification**
  - `Reinterpret` with maximal reuse
- **Reason**
  - local operator UX is valuable, and upstream UI assets should be reused as much as possible
  - however, adoption should happen through compatibility shims and sidecar-style integration rather than by forcing core runtime assumptions to match upstream product surfaces
- **Adoption rule**
  - prefer upstream UI code reuse first
  - add thin adapters/shims for local contracts
  - postpone heavy customization until after a near-stock local boot path exists
- **Status**
  - **Inventory complete; ready for a first import plan**
- **Next action**
  - use `docs/WEB_UI_COMPATIBILITY_INVENTORY.md` to define the first local sidecar / near-stock import pass

### Lane G — crabharness / orchestration product layers

- **Upstream signals**
  - `c811420`
  - `bc680fb`
  - `dcacc58`
- **Classification**
  - `Reject` for core little-crab
- **Reason**
  - valuable as an external consumer pattern, not as core runtime code

## Recommended Next Execution Order

1. **Lane A follow-through** — apply `docs/EXTRACTOR_DELTA_INVENTORY.md`
2. **Lane B** — MCP/CLI protocol compatibility inventory and first reinterpretation target
3. **Lane C** — test parity imports
4. **Lane D follow-through** — next diagnostics/output standardization pass
5. **Lane F** — web maximal-reuse compatibility inventory

## Ready Signal

It is now reasonable to say:

> little-crab can begin actual upstream OpenCrab catch-up work.

But that work should proceed **one lane at a time**, using the preserve set and fork-boundary rules already documented.
