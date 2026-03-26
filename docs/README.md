---
status: Active
source_of_truth: Yes
last_updated: 2026-03-26
superseded_by: N/A
---

# Docs Portal

This directory captures the current truth of little-crab as a local-first fork of OpenCrab.

The key meaning to preserve is simple: little-crab is not a new ontology philosophy. It is the OpenCrab grammar-and-agent loop, repackaged to run well without server-backed databases.

OpenCrab was worth preserving because it gave agents a bounded but flexible ontology workspace: the grammar constrained nonsense, while the runtime still allowed partial knowledge, incremental linking, and later gap-filling. little-crab keeps that strength and only changes the infrastructure burden.

## Canonical Docs

- [CURRENT_STATE.md](/C:/python_Github/playground/little-crab/docs/CURRENT_STATE.md)
- [ARCHITECTURE.md](/C:/python_Github/playground/little-crab/docs/ARCHITECTURE.md)
- [LAYERS.md](/C:/python_Github/playground/little-crab/docs/LAYERS.md)
- [SKILLS_INTEGRATION.md](/C:/python_Github/playground/little-crab/docs/SKILLS_INTEGRATION.md)
- [MCP_DOGFOODING.md](/C:/python_Github/playground/little-crab/docs/MCP_DOGFOODING.md)
- [ROADMAP.md](/C:/python_Github/playground/little-crab/docs/ROADMAP.md)
- [IMPACT_SUMMARY.md](/C:/python_Github/playground/little-crab/docs/IMPACT_SUMMARY.md)

## Design Notes

- [2026-03-26-lancedb-evaluation.md](/C:/python_Github/playground/little-crab/docs/2026-03-26-lancedb-evaluation.md)
- [2026-03-26-polaris-adaptation-for-little-crab.md](/C:/python_Github/playground/little-crab/docs/2026-03-26-polaris-adaptation-for-little-crab.md)

## Source Of Truth Map

- Package metadata and script registration: [pyproject.toml](/C:/python_Github/playground/little-crab/pyproject.toml)
- CLI: [opencrab/cli.py](/C:/python_Github/playground/little-crab/opencrab/cli.py)
- MCP server: [opencrab/mcp/server.py](/C:/python_Github/playground/little-crab/opencrab/mcp/server.py)
- Grammar manifest: [opencrab/grammar/manifest.py](/C:/python_Github/playground/little-crab/opencrab/grammar/manifest.py)
- Runtime store contracts: [opencrab/stores/contracts.py](/C:/python_Github/playground/little-crab/opencrab/stores/contracts.py)

## Current Runtime

little-crab is local-only. The live stack is:

- `LadybugDB` graph
- `DuckDB` operational store
- embedded `ChromaDB`

The retained compatibility surface is package/module naming:

- package name: `little-crab`
- module namespace: `opencrab`
- CLI commands: `little-crab`, `opencrab`

## Project Intent

- preserve OpenCrab's grammar, validator rules, and MCP-facing ontology workflow
- preserve the 9-space ontology coordinate system that lets agents place partial knowledge before it is complete
- preserve the agentic growth model where missing links can be filled in gradually instead of requiring a fully modeled world up front
- remove the operational burden of server-backed databases
- make local development, local MCP use, and single-machine experimentation the default path
