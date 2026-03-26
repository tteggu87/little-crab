---
status: Active
source_of_truth: Yes
last_updated: 2026-03-26
superseded_by: N/A
---

# Current State

## Summary

little-crab is a local-first fork of OpenCrab. It preserves the original MetaOntology grammar, MCP tool surface, and agentic ontology loop while removing the old service-backed storage stack.

The project goal is not to replace OpenCrab's meaning. The goal is to keep that meaning intact while making the system actually convenient to run on one machine with embedded local storage.

The specific inheritance worth keeping is the grammar-guided agent workflow: agents can classify information into the ontology's spaces, connect only what is known now, and let the graph grow as later steps add evidence, claims, policies, outcomes, or levers.

## Live Entrypoints

- Package scripts: [pyproject.toml](/C:/python_Github/playground/little-crab/pyproject.toml)
  - `little-crab = opencrab.cli:main`
  - `opencrab = opencrab.cli:main`
- CLI implementation: [opencrab/cli.py](/C:/python_Github/playground/little-crab/opencrab/cli.py)
- MCP server: [opencrab/mcp/server.py](/C:/python_Github/playground/little-crab/opencrab/mcp/server.py)
- Seed script: [scripts/seed_ontology.py](/C:/python_Github/playground/little-crab/scripts/seed_ontology.py)

## Runtime Topology

- Graph store: [opencrab/stores/ladybug_store.py](/C:/python_Github/playground/little-crab/opencrab/stores/ladybug_store.py)
- Document/event + registry/policy/analysis store: [opencrab/stores/duckdb_store.py](/C:/python_Github/playground/little-crab/opencrab/stores/duckdb_store.py)
- Vector store: [opencrab/stores/chroma_store.py](/C:/python_Github/playground/little-crab/opencrab/stores/chroma_store.py)
- Store assembly: [opencrab/stores/factory.py](/C:/python_Github/playground/little-crab/opencrab/stores/factory.py)

## Grammar + Runtime Core

- Grammar manifest: [opencrab/grammar/manifest.py](/C:/python_Github/playground/little-crab/opencrab/grammar/manifest.py)
- Grammar validation: [opencrab/grammar/validator.py](/C:/python_Github/playground/little-crab/opencrab/grammar/validator.py)
- Builder: [opencrab/ontology/builder.py](/C:/python_Github/playground/little-crab/opencrab/ontology/builder.py)
- Query: [opencrab/ontology/query.py](/C:/python_Github/playground/little-crab/opencrab/ontology/query.py)
- ReBAC: [opencrab/ontology/rebac.py](/C:/python_Github/playground/little-crab/opencrab/ontology/rebac.py)
- Impact: [opencrab/ontology/impact.py](/C:/python_Github/playground/little-crab/opencrab/ontology/impact.py)
- Extractor: [opencrab/ontology/extractor.py](/C:/python_Github/playground/little-crab/opencrab/ontology/extractor.py)

## Current Storage Truth

- There is no live Docker mode.
- There is no live Neo4j/MongoDB/PostgreSQL path.
- The module namespace remains `opencrab` intentionally for compatibility.

## Why This Fork Exists

- OpenCrab's core value is the ontology grammar plus the guided agent loop that can fill gaps incrementally.
- The original server-heavy stack made that workflow harder to run casually or locally.
- little-crab keeps the ontology behavior but swaps the infrastructure so local execution is the first-class path.

## Inherited Advantages From OpenCrab

- The 9-space grammar gives agents a stable coordinate system instead of an unbounded free-form memory dump.
- Validator rules keep node and edge creation inside a known ontology discipline.
- The MCP tool surface makes the ontology directly usable by LLM agents instead of leaving it as a passive database.
- Partial knowledge is acceptable: the runtime can start with evidence or concepts first, then grow by adding missing relations later.
- The system supports guided autonomy: agents have freedom to extend the graph, but not freedom to ignore the ontology.

## Current Truth

- `little-crab` and `opencrab` both resolve to the same CLI implementation.
- The live runtime is the embedded local stack only.
- Grammar and MCP tool naming remain aligned with upstream OpenCrab semantics.
- User-facing runtime payloads now describe local roles such as `graph`, `documents`, `registry`, and `vectors` instead of removed backend brands.

## Compatibility Boundary

- MCP tool names are preserved for OpenCrab compatibility.
- The `opencrab` Python module namespace is preserved for compatibility.
- User-facing MCP payload labels are not preserved when the old names imply removed infrastructure.
- The payload rename from backend-brand labels to local-role labels is intentional and should be treated as a breaking change for downstream JSON consumers.

Current payload label migration:

- `stores.neo4j` -> `stores.graph`
- `stores.mongodb` -> `stores.documents`
- `stores.postgres` -> `stores.registry`
- `stores.chromadb` -> `stores.vectors`

## Transitional Facts

- The `opencrab` module namespace is still live as intentional compatibility.
- Dated design docs remain visible as supporting context and are not archived away as dead history.

## Verification Snapshot

Last checked on 2026-03-26 with `py -3.12 -m pytest tests/test_cli.py tests/test_mcp.py tests/test_stores.py`:

- `py -3.12 scripts/verify_repo_intelligence.py` passed
- `tests/test_stores.py` passed
- `tests/test_mcp.py` passed
- `tests/test_cli.py` passed
- fresh `LOCAL_DATA_DIR` smoke for `status -> seed -> query` passed
- in shells where `pytest` resolves to Python 3.10, use the Python 3.12 launcher form above as the canonical verification command
