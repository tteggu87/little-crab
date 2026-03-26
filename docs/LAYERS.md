---
status: Active
source_of_truth: Yes
last_updated: 2026-03-26
superseded_by: N/A
---

# Layers

## Layer Overview

little-crab has a thin-wrapper / thick-core shape.

This layered shape exists to preserve OpenCrab's useful behavior while simplifying operations. The grammar and runtime stay rich; the deployment story gets thinner.

### Surface Layer

- CLI commands in [opencrab/cli.py](/C:/python_Github/playground/little-crab/opencrab/cli.py)
- MCP JSON-RPC server in [opencrab/mcp/server.py](/C:/python_Github/playground/little-crab/opencrab/mcp/server.py)

### Contract Layer

- Grammar manifest
- Grammar validator
- Store contracts in [opencrab/stores/contracts.py](/C:/python_Github/playground/little-crab/opencrab/stores/contracts.py)
- This is the layer that preserves OpenCrab's ontology discipline and prevents the fork from becoming a generic graph toy.

### Runtime Layer

- Builder
- Query
- ReBAC
- Impact
- Extractor
- This layer is what makes agentic growth possible: incomplete ontology structure is allowed to exist and be extended over time.

### Storage Layer

- LadybugDB graph
- DuckDB operational state
- embedded ChromaDB vectors

### Documentation + Intelligence Layer

- current docs under [docs](/C:/python_Github/playground/little-crab/docs)
- lightweight repository intelligence under [intelligence](/C:/python_Github/playground/little-crab/intelligence)

## Boundary Rules

- YAML expresses meaning and contracts.
- Python expresses execution.
- SQL files mirror canonical storage shapes, not speculative new runtimes.
- Dated design notes are supporting context, not live architecture truth.
