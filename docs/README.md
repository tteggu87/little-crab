---
status: Active
source_of_truth: Yes
last_updated: 2026-04-13
superseded_by: N/A
---

# Docs Portal

This directory captures the current truth of little-crab as a local-first fork of OpenCrab.

The key meaning to preserve is simple: little-crab is not a new ontology philosophy. It is the OpenCrab grammar-and-agent loop, repackaged to run well without server-backed databases.

OpenCrab was worth preserving because it gave agents a bounded but flexible ontology workspace: the grammar constrained nonsense, while the runtime still allowed partial knowledge, incremental linking, and later gap-filling. little-crab keeps that strength and only changes the infrastructure burden.

That preserved flexibility is now an explicit project goal, not an implied one. Future runtime and visualization work should continue to protect:

- acceptance of partial knowledge instead of hiding incomplete graph state
- support for non-English queries instead of assuming ASCII-first interaction
- enough provenance depth to explain how evidence, claims, concepts, and outcomes connect over more than a single hop

## Canonical Docs

- [CURRENT_STATE.md](CURRENT_STATE.md)
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [LAYERS.md](LAYERS.md)
- [SKILLS_INTEGRATION.md](SKILLS_INTEGRATION.md)
- [MCP_DOGFOODING.md](MCP_DOGFOODING.md)
- [ROADMAP.md](ROADMAP.md)
- [IMPACT_SUMMARY.md](IMPACT_SUMMARY.md)
- [UPSTREAM_TRAJECTORY.md](UPSTREAM_TRAJECTORY.md)
- [FORK_BOUNDARY.md](FORK_BOUNDARY.md)
- [PHASE3_ADOPTION_REVIEW.md](PHASE3_ADOPTION_REVIEW.md)
- [UPSTREAM_BACKLOG.md](UPSTREAM_BACKLOG.md)
- [EXTRACTOR_DELTA_INVENTORY.md](EXTRACTOR_DELTA_INVENTORY.md)
- [WEB_UI_COMPATIBILITY_INVENTORY.md](WEB_UI_COMPATIBILITY_INVENTORY.md)
- [MCP_PROTOCOL_COMPATIBILITY_INVENTORY.md](MCP_PROTOCOL_COMPATIBILITY_INVENTORY.md)

## Design Notes

- [2026-03-26-lancedb-evaluation.md](2026-03-26-lancedb-evaluation.md)
- [2026-03-26-polaris-adaptation-for-little-crab.md](2026-03-26-polaris-adaptation-for-little-crab.md)

## Reviews

- [docs/reviews/README.md](/C:/python_Github/playground/little-crab/docs/reviews/README.md)

## Supporting Evidence

- [AGENT_SESSION_EVIDENCE.md](AGENT_SESSION_EVIDENCE.md)
- [USAGE_GUIDE.md](USAGE_GUIDE.md)

## Source Of Truth Map

- Package metadata and script registration: [pyproject.toml](../pyproject.toml)
- CLI: [opencrab/cli.py](../opencrab/cli.py)
- MCP server: [opencrab/mcp/server.py](../opencrab/mcp/server.py)
- Grammar manifest: [opencrab/grammar/manifest.py](../opencrab/grammar/manifest.py)
- Runtime store contracts: [opencrab/stores/contracts.py](../opencrab/stores/contracts.py)

## Current Runtime

little-crab is local-only. The live stack is:

- `LadybugDB` graph
- `DuckDB` operational store
- embedded `ChromaDB`

The retained compatibility surface is package/module naming:

- package name: `little-crab`
- module namespace: `opencrab`
- CLI commands: `littlecrab`, `ltcrab`, `little-crab`, `opencrab`
- MCP tool names remain aligned with OpenCrab

Compatibility does not require keeping removed backend brand names in user-facing payloads. Runtime payloads now use local-role labels such as `graph`, `documents`, `registry`, and `vectors`.

The MCP stdio surface also now covers the baseline lifecycle hooks expected by current MCP hosts: negotiated protocol versions, `notifications/initialized`, empty resource discovery endpoints, and batched JSON-RPC follow-up requests.

Agent-facing read paths now also have a single derived context ingress through the read-only agent context pipeline. This pipeline is not a second truth system; it assembles agent-consumable context from the live local stores.

The current CLI surface now also includes `littlecrab doctor` for runtime closure checks and a lightweight staged write workflow through `stage-node`, `stage-edge`, `list-staged`, and `publish-stage`.

The current MCP surface now includes batch-safe write helpers `ontology_bulk_add_nodes` and `ontology_bulk_add_edges` in addition to the preserved single-write tools.

The current local ingestion path also includes a staged KakaoTalk workflow: bootstrap chatroom resources, participants, sources, and evidence first, then run a second local heuristic pass to promote selected evidence into concept and claim nodes.

The repo now also includes a first-pass local operator web shell plus a local API shim for read-only graph inspection and query, built to maximize reuse of upstream OpenCrab web assets before custom UI divergence.

## Project Intent

- preserve OpenCrab's grammar, validator rules, and MCP-facing ontology workflow
- preserve the 9-space ontology coordinate system that lets agents place partial knowledge before it is complete
- preserve the agentic growth model where missing links can be filled in gradually instead of requiring a fully modeled world up front
- preserve OpenCrab's flexible investigation workflow by keeping partial knowledge visible, non-English query paths viable, and provenance explanation deep enough to show multi-step connections
- remove the operational burden of server-backed databases
- make local development, local MCP use, and single-machine experimentation the default path
