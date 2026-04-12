---
status: Active
source_of_truth: Yes
last_updated: 2026-04-13
superseded_by: N/A
---

# Phase 3 Adoption Review

## Scope

Phase 3 was the first deliberate upstream trajectory catch-up pilot:

- target lane: extractor/intelligence
- implementation style: reinterpretation, not wholesale import
- preserve set: unchanged

## What Was Adopted

- upstream direction toward richer LLM-assisted extraction
- chunk-oriented extraction structure
- extraction prompt/JSON boundary concept
- explicit distinction between requested extraction mode and actual extraction mode

## What Was Reinterpreted

- Anthropic-backed extraction is **optional**, not required
- deterministic heuristic extraction remains the local-first floor
- heuristic fallback is automatic when the LLM path is unavailable or fails
- MCP tool wording now reflects local-first extraction with optional enrichment rather than network-first extraction

## What Was Not Adopted

- mandatory external LLM dependency for extraction
- any remote/server-first execution surface
- unrelated upstream product layers

## Outcome

The pilot succeeded in demonstrating that little-crab can follow an upstream capability trajectory while preserving:

- local-first runtime
- current CLI/MCP behavior
- explicit backend divergence

This validates the thin-fork approach for aligned upstream lanes.

## Reuse Result

### Successful

- capability direction reuse
- prompt/chunking pattern reuse
- optional enrichment seam

### Still Divergent

- provider dependency remains optional in little-crab
- deterministic heuristic bootstrap remains part of the default contract
- local-first runtime assumptions remain stronger than upstream

## Adoption Decision

**Adopted as a successful pilot.**

Phase 3 should be treated as proof that:

- aligned upstream capability lanes can be absorbed
- reinterpretation is often better than direct merge
- preserve-set discipline can coexist with upstream catch-up

## Residual Risks

- provider-specific response quality still affects the optional LLM path
- future extractor/intelligence catch-up may still expose hidden backend assumptions
- output shape must remain stable as more diagnostics are added

## Recommendation For Next Lane

The next aligned lane should focus on:

- automation-ready outputs
- explicit diagnostics
- deterministic machine-readable summaries

These continue the same trajectory without widening into upstream product surfaces.
