---
status: Active
source_of_truth: No
last_updated: 2026-03-26
superseded_by: N/A
---

# Impact Summary

## Changed Files

Canonical docs and intelligence bootstrap were added:

- [README.md](/C:/python_Github/playground/little-crab/README.md)
- [AGENTS.md](/C:/python_Github/playground/little-crab/AGENTS.md)
- [docs/README.md](/C:/python_Github/playground/little-crab/docs/README.md)
- [docs/CURRENT_STATE.md](/C:/python_Github/playground/little-crab/docs/CURRENT_STATE.md)
- [docs/ARCHITECTURE.md](/C:/python_Github/playground/little-crab/docs/ARCHITECTURE.md)
- [docs/LAYERS.md](/C:/python_Github/playground/little-crab/docs/LAYERS.md)
- [docs/MCP_DOGFOODING.md](/C:/python_Github/playground/little-crab/docs/MCP_DOGFOODING.md)
- [docs/SKILLS_INTEGRATION.md](/C:/python_Github/playground/little-crab/docs/SKILLS_INTEGRATION.md)
- [docs/ROADMAP.md](/C:/python_Github/playground/little-crab/docs/ROADMAP.md)
- [docs/IMPACT_SUMMARY.md](/C:/python_Github/playground/little-crab/docs/IMPACT_SUMMARY.md)
- [opencrab/mcp/tools.py](/C:/python_Github/playground/little-crab/opencrab/mcp/tools.py)
- [opencrab/ontology/builder.py](/C:/python_Github/playground/little-crab/opencrab/ontology/builder.py)
- [opencrab/ontology/query.py](/C:/python_Github/playground/little-crab/opencrab/ontology/query.py)
- [intelligence/glossary.yaml](/C:/python_Github/playground/little-crab/intelligence/glossary.yaml)
- [intelligence/manifests/actions.yaml](/C:/python_Github/playground/little-crab/intelligence/manifests/actions.yaml)
- [intelligence/manifests/entities.yaml](/C:/python_Github/playground/little-crab/intelligence/manifests/entities.yaml)
- [intelligence/manifests/datasets.yaml](/C:/python_Github/playground/little-crab/intelligence/manifests/datasets.yaml)
- [intelligence/handlers/mcp_request.yaml](/C:/python_Github/playground/little-crab/intelligence/handlers/mcp_request.yaml)
- [intelligence/policies/repo_rules.yaml](/C:/python_Github/playground/little-crab/intelligence/policies/repo_rules.yaml)
- [intelligence/registry/capabilities.yaml](/C:/python_Github/playground/little-crab/intelligence/registry/capabilities.yaml)
- [intelligence/schemas/duckdb_contracts.sql](/C:/python_Github/playground/little-crab/intelligence/schemas/duckdb_contracts.sql)
- [scripts/dogfood_mcp.py](/C:/python_Github/playground/little-crab/scripts/dogfood_mcp.py)
- [scripts/verify_repo_intelligence.py](/C:/python_Github/playground/little-crab/scripts/verify_repo_intelligence.py)
- [Makefile](/C:/python_Github/playground/little-crab/Makefile)
- [tests/test_mcp.py](/C:/python_Github/playground/little-crab/tests/test_mcp.py)
- [tests/test_stores.py](/C:/python_Github/playground/little-crab/tests/test_stores.py)
- [tests/test_repo_intelligence.py](/C:/python_Github/playground/little-crab/tests/test_repo_intelligence.py)

## Checked Not Changed

- [docs/2026-03-26-lancedb-evaluation.md](/C:/python_Github/playground/little-crab/docs/2026-03-26-lancedb-evaluation.md)
- [docs/2026-03-26-polaris-adaptation-for-little-crab.md](/C:/python_Github/playground/little-crab/docs/2026-03-26-polaris-adaptation-for-little-crab.md)

## Current vs Legacy Split

- Current:
  - local-only runtime
  - LadybugDB + DuckDB + embedded ChromaDB
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
- The payload label rename is intentional and should be treated as a breaking change for consumers that parse `stores.*` keys directly.
- Added a repeatable repository intelligence consistency check driven from live CLI, MCP, and DuckDB code paths.

Payload migration map:

- `stores.neo4j` -> `stores.graph`
- `stores.mongodb` -> `stores.documents`
- `stores.postgres` -> `stores.registry`
- `stores.chromadb` -> `stores.vectors`

## Validator Summary

- Validator run from the bootstrap skill completed after the docs/intelligence pass.
- Current expectation is validator-clean except for the warning emitted when no changed-files list is supplied.
- Runtime verification was rechecked on 2026-03-26 with `py -3.12 -m pytest tests/test_cli.py tests/test_mcp.py tests/test_stores.py` and all 68 tests passed.
- Repository intelligence verification is now automated via `scripts/verify_repo_intelligence.py`.
- The repeatable local MCP dogfood path is now documented in `docs/MCP_DOGFOODING.md` and automated via `scripts/dogfood_mcp.py`.
