---
status: Active
source_of_truth: Yes
last_updated: 2026-04-13
superseded_by: N/A
---

# Current State

## Summary

little-crab is a local-first fork of OpenCrab. It preserves the original MetaOntology grammar, MCP tool surface, and agentic ontology loop while removing the old service-backed storage stack.

The project goal is not to replace OpenCrab's meaning. The goal is to keep that meaning intact while making the system actually convenient to run on one machine with embedded local storage.

The specific inheritance worth keeping is the grammar-guided agent workflow: agents can classify information into the ontology's spaces, connect only what is known now, and let the graph grow as later steps add evidence, claims, policies, outcomes, or levers.

## Live Entrypoints

- Package scripts: [pyproject.toml](/C:/python_Github/playground/little-crab/pyproject.toml)
  - `littlecrab = opencrab.cli:main`
  - `ltcrab = opencrab.cli:main`
  - `little-crab = opencrab.cli:main`
  - `opencrab = opencrab.cli:main`
- CLI implementation: [opencrab/cli.py](/C:/python_Github/playground/little-crab/opencrab/cli.py)
- MCP server: [opencrab/mcp/server.py](/C:/python_Github/playground/little-crab/opencrab/mcp/server.py)
- Seed script: [scripts/seed_ontology.py](/C:/python_Github/playground/little-crab/scripts/seed_ontology.py)
- KakaoTalk importer: [scripts/import_kakaotalk_csv.py](/C:/python_Github/playground/little-crab/scripts/import_kakaotalk_csv.py)
- KakaoTalk semantic promotion: [scripts/promote_kakaotalk_semantics.py](/C:/python_Github/playground/little-crab/scripts/promote_kakaotalk_semantics.py)

## Runtime Topology

- Graph store: [opencrab/stores/ladybug_store.py](/C:/python_Github/playground/little-crab/opencrab/stores/ladybug_store.py)
- Document/event + registry/policy/analysis store: [opencrab/stores/duckdb_store.py](/C:/python_Github/playground/little-crab/opencrab/stores/duckdb_store.py)
- Vector store: [opencrab/stores/chroma_store.py](/C:/python_Github/playground/little-crab/opencrab/stores/chroma_store.py)
- Store assembly: [opencrab/stores/factory.py](/C:/python_Github/playground/little-crab/opencrab/stores/factory.py)

## Grammar + Runtime Core

- Grammar manifest: [opencrab/grammar/manifest.py](/C:/python_Github/playground/little-crab/opencrab/grammar/manifest.py)
- Grammar validation: [opencrab/grammar/validator.py](/C:/python_Github/playground/little-crab/opencrab/grammar/validator.py)
- Builder: [opencrab/ontology/builder.py](/C:/python_Github/playground/little-crab/opencrab/ontology/builder.py)
- Agent context pipeline: [opencrab/ontology/context_pipeline.py](/C:/python_Github/playground/little-crab/opencrab/ontology/context_pipeline.py)
- Query: [opencrab/ontology/query.py](/C:/python_Github/playground/little-crab/opencrab/ontology/query.py)
- ReBAC: [opencrab/ontology/rebac.py](/C:/python_Github/playground/little-crab/opencrab/ontology/rebac.py)
- Impact: [opencrab/ontology/impact.py](/C:/python_Github/playground/little-crab/opencrab/ontology/impact.py)
- Extractor: [opencrab/ontology/extractor.py](/C:/python_Github/playground/little-crab/opencrab/ontology/extractor.py)

## Current Storage Truth

- There is no live Docker mode.
- There is no live Neo4j/MongoDB/PostgreSQL path.
- The module namespace remains `opencrab` intentionally for compatibility.
- Canonical ontology entity and relation truth lives in Ladybug.
- Canonical documentary, provenance, registry, policy, audit, impact, and workflow draft state lives in DuckDB.
- `staged_operations` in DuckDB is workflow state only; it is not canonical ontology truth until a staged write is published successfully.
- Chroma remains a derived retrieval index, not a canonical truth store.

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

## Explicit Preservation Targets

little-crab now treats the following OpenCrab flexibility traits as explicit preservation goals:

- `partial knowledge visibility`: incomplete graph state should remain visible enough for later gap-filling instead of being flattened away by read models
- `non-English query viability`: retrieval and investigation paths should not assume ASCII-only questions
- `provenance depth`: evidence-to-claim-to-concept-to-outcome reasoning should remain explainable across multiple hops when the data supports it

## Current Truth

- `littlecrab` is the canonical user-facing CLI command.
- `ltcrab` is the supported short CLI alias.
- `little-crab` remains available as a legacy CLI alias.
- `opencrab` remains available as a deprecated compatibility CLI alias.
- The live runtime is the embedded local stack only.
- The embedded Chroma vector path now supports either the default local ONNX embedding function or an Ollama-backed embedding model selected through environment configuration.
- Grammar and MCP tool naming remain aligned with upstream OpenCrab semantics.
- The MCP stdio server now accepts negotiated protocol versions, `notifications/initialized`, `resources/list`, `resources/templates/list`, and batched JSON-RPC requests.
- Successful node and edge structural writes now follow graph persistence first; registry rows and success audits are emitted only after the graph record itself persists, while failed graph writes are tracked as failed attempts instead of live ontology truth.
- `project` and `source_id_prefix` query filters intentionally keep retrieval inside caller scope by restricting vector results and disabling graph expansion.
- Embedded runtime state can be rebuilt in-process for tests or host reloads with `opencrab.mcp.tools.reset_runtime_state()`.
- `ontology_query` now assembles a derived `context` bundle through the read-only agent context pipeline while keeping legacy `results` for compatibility.
- `littlecrab query` and `ontology_query` now surface trustability-oriented summary counts for confirmed facts, inferred facts, supporting evidence, provenance paths, and missing links.
- Agent-context enrichment remains best-effort: supporting evidence or policy hint lookup failures degrade into `missing_links` and `uncertainty.notes` instead of aborting the full query response.
- Agent-context enrichment now batches DuckDB-backed source, node-document, and policy lookups when the local store supports it, then falls back to per-item lookup if the batch path fails.
- The agent context bundle is not a second SSOT; it is derived from the live local stores for agent-facing reasoning only.
- `ontology_extract` now follows the first extractor trajectory catch-up path: deterministic heuristic bootstrap remains the default, and Anthropic-backed chunked extraction is opt-in only when a non-heuristic model is explicitly requested in a configured environment.
- User-facing runtime payloads now describe local roles such as `graph`, `documents`, `registry`, and `vectors` instead of removed backend brands.
- `littlecrab doctor` now reports current runtime health and also runs an isolated write -> ingest -> query closure smoke.
- `littlecrab ingest` now performs chunked vector upserts and document-source persistence by default, with per-file fallback only when the batch path fails.
- `littlecrab stage-node`, `stage-edge`, `list-staged`, and `publish-stage` now provide a lightweight draft-before-publish workflow.
- `ontology_bulk_add_nodes` and `ontology_bulk_add_edges` now provide batch-safe MCP write paths without changing the preserved single-write tool names.
- `LadybugStore.find_neighbors` and `find_path` now reuse a traversal-scoped Ladybug connection instead of reopening handles for each adjacency query inside the same traversal.
- `scripts/import_kakaotalk_csv.py` now provides a conservative signal-first room-corpus bootstrap path that imports KakaoTalk CSV exports as chatroom resources, participant subjects, per-message source records, and promoted evidence/vector records for higher-signal messages.
- `scripts/promote_kakaotalk_semantics.py` now provides a second KakaoTalk ontology-growth pass that scans imported evidence nodes and promotes conservative concept, claim, and concept-to-concept structure with local heuristics.
- thin-fork realignment work now treats current little-crab behavior as a locked preserve set while reducing divergence in high-conflict coordinator files; see `docs/FORK_BOUNDARY.md` and `docs/UPSTREAM_TRAJECTORY.md`.

## Compatibility Boundary

- MCP tool names are preserved for OpenCrab compatibility.
- The canonical CLI command is `littlecrab`.
- The `ltcrab` CLI name is preserved as a short alias.
- The `little-crab` CLI name is preserved as a legacy alias.
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

Last checked on 2026-03-27 with `py -3.12 -m pytest tests/test_cli.py tests/test_mcp.py tests/test_stores.py tests/test_repo_intelligence.py`:

- `py -3.12 -m pytest tests/test_cli.py tests/test_mcp.py tests/test_stores.py tests/test_repo_intelligence.py` passed
- `93` tests passed in the targeted verification slice
- `py -3.12 scripts/verify_repo_intelligence.py` passed
- `tests/test_cli.py` now covers `doctor`, trustability-oriented `query`, and staged publish flow
- `tests/test_mcp.py` now covers the 11-tool MCP surface including batch node and edge writes
- `tests/test_stores.py` now covers `staged_operations` lifecycle persistence
- in shells where `pytest` resolves to Python 3.10, use the Python 3.12 launcher form above as the canonical verification command
