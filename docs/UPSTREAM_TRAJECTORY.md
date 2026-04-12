---
status: Active
source_of_truth: Yes
last_updated: 2026-04-13
superseded_by: N/A
---

# OpenCrab Upstream Trajectory Catch-up Strategy

## Intent

little-crab should not try to mirror OpenCrab commit-for-commit.

The goal is to follow the **direction of upstream evolution** wherever that direction improves the shared ontology runtime, while keeping little-crab's defining choice intact:

- OpenCrab core semantics stay as reusable as possible
- little-crab remains the local-first backend/profile variant

In practice, this means treating little-crab as a **thin fork around backend/runtime profile differences**, not as an unrelated product line.

## Current Strategic Conclusion

Compared to upstream OpenCrab, little-crab should:

1. **maximize reuse** of core ontology, grammar, MCP, and agent-facing semantics
2. **keep backend divergence explicit and narrow**
3. **avoid importing upstream product surfaces wholesale** when they widen scope beyond the local-first runtime
4. **catch up on trajectories**, not raw commit volume

## Preserve-Set Assumption

This strategy assumes the current little-crab preserve set remains locked while trajectory catch-up proceeds.

The preserve set is defined in:

- `docs/CURRENT_STATE.md`
- `docs/FORK_BOUNDARY.md`

## What "Catch-up" Means Here

Catch-up is not:

- blindly merging upstream
- recreating every upstream deployment surface
- turning little-crab into a SaaS or orchestration platform

Catch-up means:

- identify what OpenCrab is getting better at
- decide whether that capability matters for little-crab
- reinterpret it in a local-first way when needed
- keep shared contracts and semantics close enough that future upstream reuse stays cheap

## Upstream Trajectory Buckets

### 1. Agent capability and ontology intelligence

Examples:

- extractor improvements
- richer query/retrieval assembly
- semantic scoring or trustability-related runtime improvements

Decision: **High-priority catch-up**

Reason:

- this is aligned with the shared OpenCrab/little-crab ontology mission
- it usually improves the core runtime rather than widening product scope

Preferred adoption mode:

- reuse upstream logic where possible
- manually port when provider assumptions or backend assumptions differ

### 2. Transport and runtime surface expansion

Examples:

- remote MCP transport
- additional server entrypoints
- protocol adapter layers

Decision: **Catch up on structure, not necessarily on shipped surface**

Reason:

- transport abstraction is useful
- shipping hosted/server-first runtime paths is not currently little-crab's primary goal

Preferred adoption mode:

- preserve transport-agnostic internal boundaries
- do not automatically adopt remote deployment/runtime obligations

### 3. Productization and operator UX

Examples:

- dashboards
- web graph views
- richer operator surfaces

Decision: **Selective inspiration only**

Reason:

- the idea of better operator experience is good
- importing full product/UI layers would make the fork much thicker

Preferred adoption mode:

- keep improving local operator workflows
- avoid importing full upstream web app surfaces into core little-crab unless product intent changes

### 4. Harness/orchestration/platform layers

Examples:

- crabharness
- mission control planes
- worker orchestration products

Decision: **Do not import into core little-crab**

Reason:

- this is an upper-layer product/system
- little-crab should instead remain a runtime that external orchestration can call cleanly

Preferred adoption mode:

- improve machine-readable outputs, batch APIs, and deterministic behavior
- keep orchestration outside the runtime core

## Reuse Matrix

### Reuse as directly as possible

- `opencrab/grammar/*`
- validator semantics
- ontology contracts and shared reasoning semantics
- MCP protocol handling expectations
- tool naming compatibility
- extractor direction and capability goals

### Reuse with a local adapter boundary

- `opencrab/cli.py`
- `opencrab/mcp/tools.py`
- `opencrab/config.py`
- `opencrab/ontology/query.py`
- `opencrab/ontology/context_pipeline.py`
- `opencrab/ontology/extractor.py`

Rule:

- keep these layers as thin as possible
- push little-crab-specific behavior downward into backend/profile adapters instead of hard-forking the whole file

### Keep fork-specific

- `opencrab/stores/duckdb_store.py`
- `opencrab/stores/ladybug_store.py`
- local embedded Chroma profile details
- local runtime assembly choices in `opencrab/stores/factory.py`
- docs/intelligence/AGENTS operational overlays

Rule:

- backend divergence is allowed here
- but the contracts seen by upper layers should remain stable and upstream-friendly

## Review Rubric

For execution planning, the canonical upstream-delta review rubric is:

- **Adopt**
- **Reinterpret**
- **Defer**
- **Reject**

The detailed criteria for those buckets live in `docs/FORK_BOUNDARY.md`.

## Thin-Fork Target Shape

The desired architecture is:

- **OpenCrab-like core**
  - grammar
  - validation
  - ontology semantics
  - MCP-facing contracts
  - CLI/MCP behavior
- **little-crab adapter layer**
  - local-first backend resolution
  - Ladybug/DuckDB/embedded Chroma integration
  - local operator ergonomics
  - local docs/intelligence overlays

The fork gets healthier as the "adapter layer" gets smaller.

## Practical Migration Priorities

### Priority 1 — Keep backend seams clean

Continue narrowing the fork so upper ontology/runtime layers do not encode backend assumptions directly.

Success signs:

- more logic lives behind store contracts
- fewer upstream conflicts in ontology/query/CLI/MCP files

### Priority 2 — Reduce divergence in high-conflict coordinator files

Primary targets:

- `opencrab/cli.py`
- `opencrab/mcp/tools.py`
- `opencrab/config.py`
- `opencrab/stores/factory.py`

Goal:

- keep them thin and adapter-oriented
- avoid embedding broad little-crab-only policy in these files when a lower layer can own it

### Priority 3 — Pilot upstream trajectory catch-up on extractor/intelligence

The first deliberate catch-up lane should be extractor/agent capability work.

Why:

- highest strategic alignment
- less product-surface risk than web/server/harness lanes
- most likely to improve little-crab without redefining it

### Priority 4 — Keep external orchestration optional

little-crab should become easier for orchestration systems to use without embedding those orchestration systems into the core repo.

Desired properties:

- stable JSON payloads
- batch-safe APIs
- deterministic CLI/MCP behavior
- explicit diagnostics

## Upstream Review Workflow

Every upstream review should classify changes into one of four lanes:

### Lane A — Adopt eagerly

- grammar and validator fixes
- ontology core semantics improvements
- extractor and agent-intelligence improvements
- protocol/test/quality fixes

### Lane B — Adopt with reinterpretation

- CLI changes
- MCP tool implementation changes
- query/runtime improvements that assume a different backend stack

### Lane C — Observe but do not import wholesale

- remote server surfaces
- deployment-specific additions
- product UX shells

### Lane D — Keep external to core little-crab

- harness/orchestration products
- broad app/platform layers

## Decision Heuristic

When evaluating an upstream change, ask:

1. Does this improve the shared ontology runtime?
2. Can this be expressed without expanding little-crab beyond local-first runtime scope?
3. Can it fit behind existing contracts or a thin adapter?
4. Will taking it make future upstream catch-up cheaper?

If the answers are mostly "yes", it is a good catch-up candidate.

## Non-Goals

This strategy does **not** commit little-crab to:

- becoming server-first
- becoming a full web product
- embedding orchestration/harness systems into the core repo
- eliminating all fork-specific backend code

## Near-Term Next Actions

1. Keep documenting upstream-vs-fork ownership boundaries.
2. Continue reducing divergence in `cli.py`, `mcp/tools.py`, `config.py`, and `stores/factory.py`.
3. Review upstream extractor/intelligence changes as the first deliberate catch-up lane.
4. Treat "DB/profile difference only" as the default test for whether a new divergence is justified.
