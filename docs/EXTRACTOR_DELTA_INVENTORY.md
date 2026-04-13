---
status: Active
source_of_truth: Yes
last_updated: 2026-04-13
superseded_by: N/A
---

# Extractor / Intelligence Delta Inventory

## Purpose

This document records the first concrete upstream-delta inventory for the
OpenCrab → little-crab catch-up program.

It is intentionally scoped to the **extractor / adjacent intelligence** lane.

## Upstream Signal

Primary upstream signal:

- `bc0466e` — `feat: add LLM extractor + gitignore cleanup`

Relevant extractor changes in that upstream line include:

- Anthropic-backed extraction flow
- chunk-based extraction strategy
- grammar prompt + JSON contract for nodes/edges
- file-based extraction entrypoint

## Delta Classification

### 1. LLM-backed extraction direction

- **Upstream shape**
  - Anthropic/Claude extraction is the primary extractor path
- **little-crab classification**
  - **Reinterpret**
- **Decision**
  - Adopt the capability direction, but not as a required runtime dependency
- **Current little-crab state**
  - heuristic extraction remains the default floor
  - Anthropic-backed chunked enrichment is optional
- **Reason**
  - preserves local-first runtime while validating the upstream direction

### 2. Chunk-based extraction strategy

- **Upstream shape**
  - split text into chunks before extraction
- **little-crab classification**
  - **Adopt**
- **Decision**
  - adopted
- **Current little-crab state**
  - optional LLM path now uses chunked extraction
- **Reason**
  - chunking improves future compatibility and is not in tension with local-first behavior

### 3. Grammar-prompt / JSON extraction contract

- **Upstream shape**
  - extraction prompt carries the 9-space grammar summary and expects JSON node/edge output
- **little-crab classification**
  - **Adopt / Reinterpret**
- **Decision**
  - adopt the shape, reinterpret it as an optional enrichment path
- **Current little-crab state**
  - grammar summary and JSON parsing seam added for the optional LLM path
- **Reason**
  - this is reusable core behavior, but should not displace heuristic fallback

### 4. `extract_from_file()` convenience path

- **Upstream shape**
  - file-based extraction helper
- **little-crab classification**
  - **Adopt**
- **Decision**
  - adopted
- **Reason**
  - low-risk convenience and future CLI parity aid

### 5. Network-first extractor assumption

- **Upstream shape**
  - extractor implementation assumes external Anthropic use when enabled
- **little-crab classification**
  - **Reject as default / Reinterpret as optional**
- **Decision**
  - do not make network extraction the default behavior
- **Reason**
  - violates the preserve set if heuristic local extraction ceases to work without credentials

## Adjacent Intelligence Follow-through

These items remain open for the next extractor/intelligence follow-through step:

1. compare upstream prompt/schema details more precisely
2. decide whether adjacent intelligence logic beyond extraction should live in Lane A or in a new lane
3. decide whether provider abstraction should widen beyond Anthropic
4. evaluate whether extraction diagnostics should be standardized across more CLI/MCP paths

## Outcome Of This Inventory

The extractor lane is now no longer "exploratory only".

It has a concrete policy:

- **Adopt**
  - chunking
  - file extraction convenience
  - grammar-prompt/JSON structure where useful
- **Reinterpret**
  - LLM-backed extraction as optional enrichment
- **Reject as default**
  - mandatory network-first extraction behavior

## Next Action

The next extractor/intelligence follow-through pass should focus on:

- prompt/schema delta comparison against upstream
- provider abstraction review
- deciding whether adjacent intelligence stays in Lane A or splits into a new lane
