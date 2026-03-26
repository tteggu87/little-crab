---
status: Active
source_of_truth: No
last_updated: 2026-03-26
superseded_by: N/A
---

# Agent Session Evidence

This note tracks checked-in evidence generated from real stdio MCP sessions against the local little-crab runtime.

The goal is not to replace tests. The goal is to preserve a concrete protocol-level record that the agent-facing workflow still works end to end.

## Canonical Artifact Path

- [docs/evidence/agent_sessions/2026-03-26-canonical](/C:/python_Github/playground/little-crab/docs/evidence/agent_sessions/2026-03-26-canonical)

## Refresh Command

On this repository's Windows setup, regenerate evidence with:

```bash
py -3.12 scripts/dogfood_mcp.py --transcript-dir docs/evidence/agent_sessions/latest
```

Then compare the refreshed evidence with the canonical checked-in directory before replacing it.

## What The Evidence Contains

- sanitized raw MCP transcript records
- per-scenario JSON summaries
- a Markdown summary for human review

## Current Covered Flows

- grammar inspection and validated graph growth
- local ingest, extraction, and query
- ReBAC, impact, and lever simulation
