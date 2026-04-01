---
status: Active
source_of_truth: No
last_updated: 2026-03-27
superseded_by: N/A
---

# Impact Summary

## Changed Files

Canonical docs and intelligence bootstrap were added:

- [README.md](../README.md)
- [AGENTS.md](../AGENTS.md)
- [docs/README.md](README.md)
- [docs/CURRENT_STATE.md](CURRENT_STATE.md)
- [docs/ARCHITECTURE.md](ARCHITECTURE.md)
- [docs/LAYERS.md](LAYERS.md)
- [docs/MCP_DOGFOODING.md](MCP_DOGFOODING.md)
- [docs/AGENT_SESSION_EVIDENCE.md](AGENT_SESSION_EVIDENCE.md)
- [docs/USAGE_GUIDE.md](USAGE_GUIDE.md)
- [docs/evidence/agent_sessions/2026-03-26-canonical](evidence/agent_sessions/2026-03-26-canonical)
- [docs/SKILLS_INTEGRATION.md](SKILLS_INTEGRATION.md)
- [docs/ROADMAP.md](ROADMAP.md)
- [docs/IMPACT_SUMMARY.md](IMPACT_SUMMARY.md)
- [opencrab/ontology/context_pipeline.py](../opencrab/ontology/context_pipeline.py)
- [opencrab/mcp/tools.py](../opencrab/mcp/tools.py)
- [opencrab/ontology/builder.py](../opencrab/ontology/builder.py)
- [opencrab/ontology/query.py](../opencrab/ontology/query.py)
- [intelligence/glossary.yaml](../intelligence/glossary.yaml)
- [intelligence/manifests/actions.yaml](../intelligence/manifests/actions.yaml)
- [intelligence/manifests/entities.yaml](../intelligence/manifests/entities.yaml)
- [intelligence/manifests/datasets.yaml](../intelligence/manifests/datasets.yaml)
- [intelligence/handlers/mcp_request.yaml](../intelligence/handlers/mcp_request.yaml)
- [intelligence/policies/repo_rules.yaml](../intelligence/policies/repo_rules.yaml)
- [intelligence/registry/capabilities.yaml](../intelligence/registry/capabilities.yaml)
- [intelligence/schemas/duckdb_contracts.sql](../intelligence/schemas/duckdb_contracts.sql)
- [scripts/dogfood_mcp.py](../scripts/dogfood_mcp.py)
- [scripts/verify_repo_intelligence.py](../scripts/verify_repo_intelligence.py)
- [Makefile](../Makefile)
- [tests/test_mcp.py](../tests/test_mcp.py)
- [tests/test_stores.py](../tests/test_stores.py)
- [tests/test_repo_intelligence.py](../tests/test_repo_intelligence.py)

## Checked Not Changed

- [docs/2026-03-26-lancedb-evaluation.md](2026-03-26-lancedb-evaluation.md)
- [docs/2026-03-26-polaris-adaptation-for-little-crab.md](2026-03-26-polaris-adaptation-for-little-crab.md)

## Current vs Legacy Split

- Current:
- local-only runtime
- LadybugDB + DuckDB + embedded ChromaDB
- distributed canonical truth ownership across Ladybug and DuckDB
- read-only derived agent context assembly through `AgentContextPipeline`
- `little-crab` package name
- `opencrab` module compatibility namespace
- Legacy retained intentionally:
  - naming continuity from OpenCrab in grammar and module paths
- Legacy removed:
  - Neo4j, MongoDB, PostgreSQL, Docker-first stack

## Remaining Drift

- Some module/docstrings still reference `opencrab` by namespace for compatibility.
- Dated design notes are still stored directly under `docs/` and not yet reclassified into the supporting design-note directories.
- Some shell environments may resolve bare `pytest` to Python 3.10 even though the canonical project runtime requires Python 3.11+.

## New Terms Or Contracts

- Added a minimal glossary for project/runtime vocabulary.
- Added action, entity, dataset, capability, handler, policy, and schema manifests under `intelligence/`.
- User-facing runtime payloads were aligned to local role names: `graph`, `documents`, `registry`, and `vectors`.
- Added a read-only agent context bundle layer for MCP query responses without introducing a second source-of-truth.
- The payload label rename is intentional and should be treated as a breaking change for consumers that parse `stores.*` keys directly.
- Added a repeatable repository intelligence consistency check driven from live CLI, MCP, and DuckDB code paths.
- Added repeatable MCP session evidence capture from the local stdio server via `--transcript-dir`.

Payload migration map:

- `stores.neo4j` -> `stores.graph`
- `stores.mongodb` -> `stores.documents`
- `stores.postgres` -> `stores.registry`
- `stores.chromadb` -> `stores.vectors`

## Validator Summary

- Validator run from the bootstrap skill completed after the docs/intelligence pass.
- Current expectation is validator-clean except for the warning emitted when no changed-files list is supplied.
- Runtime verification was rechecked on 2026-03-27 with `py -3.12 -m pytest tests/test_cli.py tests/test_mcp.py tests/test_stores.py` and all 78 tests passed.
- Repository intelligence verification is now automated via `scripts/verify_repo_intelligence.py`.
- The repeatable local MCP dogfood path is now documented in `docs/MCP_DOGFOODING.md` and automated via `scripts/dogfood_mcp.py`.
- Checked-in agent-session evidence is now documented in `docs/AGENT_SESSION_EVIDENCE.md`.
