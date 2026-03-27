---
status: Active
source_of_truth: Yes
last_updated: 2026-03-27
superseded_by: N/A
---

# Layers

## Layer Overview

little-crab has a thin-wrapper / thick-core shape.

This layered shape exists to preserve OpenCrab's useful behavior while simplifying operations. The grammar and runtime stay rich; the deployment story gets thinner.

### Surface Layer

- CLI commands in [opencrab/cli.py](/C:/python_Github/playground/little-crab/opencrab/cli.py)
- MCP JSON-RPC server in [opencrab/mcp/server.py](/C:/python_Github/playground/little-crab/opencrab/mcp/server.py)
- Current CLI surface includes runtime health inspection and staged publish helpers in addition to the preserved OpenCrab-style read/write commands.

### Contract Layer

- Grammar manifest
- Grammar validator
- Store contracts in [opencrab/stores/contracts.py](/C:/python_Github/playground/little-crab/opencrab/stores/contracts.py)
- This is the layer that preserves OpenCrab's ontology discipline and prevents the fork from becoming a generic graph toy.

### Runtime Layer

- Builder
- Agent context pipeline
- Query
- ReBAC
- Impact
- Extractor
- This layer is what makes agentic growth possible: incomplete ontology structure is allowed to exist and be extended over time.

### Agent Context Layer

- Derived read-only context bundle assembly for agent-facing reasoning
- Current implementation entrypoint: [opencrab/ontology/context_pipeline.py](/C:/python_Github/playground/little-crab/opencrab/ontology/context_pipeline.py)
- This layer gives agents one stable reasoning ingress even though canonical truth remains distributed across the live local stores.
- Current bundle outputs distinguish confirmed vs inferred facts and surface evidence, provenance paths, missing links, and uncertainty notes.

### Storage Layer

- LadybugDB graph
- DuckDB operational and workflow state
- embedded ChromaDB vectors

### Documentation + Intelligence Layer

- current docs under [docs](/C:/python_Github/playground/little-crab/docs)
- lightweight repository intelligence under [intelligence](/C:/python_Github/playground/little-crab/intelligence)

## Boundary Rules

- YAML expresses meaning and contracts.
- Python expresses execution.
- SQL files mirror canonical storage shapes, not speculative new runtimes.
- Ladybug and DuckDB own canonical truth in their respective domains.
- Staged operations in DuckDB are workflow drafts, not canonical ontology truth.
- Chroma and the agent context bundle are derived layers, not canonical source-of-truth layers.
- Dated design notes are supporting context, not live architecture truth.
