# little-crab

little-crab is a local-first fork of OpenCrab built to keep the original ontology grammar and agentic workflow while removing the heavy server database stack.

This project exists to make the OpenCrab idea run well on a single machine. Instead of requiring Neo4j, MongoDB, and PostgreSQL services, little-crab keeps the grammar, validator, MCP tool surface, and agentic ontology loop, but runs them on embedded local stores.

little-crab keeps the original MetaOntology grammar, validator behavior, MCP tool surface, and agentic ontology loop, but removes the legacy service stack. The runtime is now embedded only:

- `LadybugDB` for graph traversal
- `DuckDB` for documents, audit events, registry, policies, impacts, and simulations
- embedded `ChromaDB` for vectors

The Python package name is `little-crab`. The CLI exposes both `little-crab` and `opencrab` entrypoints for compatibility.

---

## What Stays the Same

- 9-space MetaOntology grammar
- grammar validation rules
- MCP tool names:
  - `ontology_manifest`
  - `ontology_add_node`
  - `ontology_add_edge`
  - `ontology_query`
  - `ontology_impact`
  - `ontology_rebac_check`
  - `ontology_lever_simulate`
  - `ontology_extract`
  - `ontology_ingest`
- guided, partial-knowledge ontology workflow for agent use

## What Changed

- no Docker requirement
- no Neo4j, MongoDB, or PostgreSQL dependency
- local-first runtime only
- designed to preserve OpenCrab semantics while making day-to-day local use practical

---

## Quick Start

### 1. Install

```bash
python -m pip install -e ".[dev]"
```

### 2. Initialize local config

```bash
little-crab init
```

This creates `.env` with:

```env
STORAGE_MODE=local
LOCAL_DATA_DIR=./opencrab_data
CHROMA_COLLECTION=little_crab_vectors
MCP_SERVER_NAME=little-crab
MCP_SERVER_VERSION=0.1.0
LOG_LEVEL=INFO
```

### 3. Check embedded stores

```bash
little-crab status
```

### 4. Seed example data

```bash
python scripts/seed_ontology.py
```

### 5. Run a query

```bash
little-crab query "system performance and error rates"
little-crab manifest
```

### 6. Connect as an MCP server

```bash
claude mcp add little-crab -- little-crab serve
```

You can also keep using the compatibility alias:

```bash
claude mcp add little-crab -- opencrab serve
```

---

## Claude Code MCP Configuration

```json
{
  "mcpServers": {
    "little-crab": {
      "command": "little-crab",
      "args": ["serve"],
      "env": {
        "LOCAL_DATA_DIR": "./opencrab_data"
      }
    }
  }
}
```

---

## CLI Reference

```text
little-crab init              Create .env from template
little-crab serve             Start MCP server (stdio)
little-crab status            Check embedded store connections
little-crab ingest <path>     Ingest files into vector store
little-crab query <question>  Run a hybrid query
little-crab manifest          Print MetaOntology grammar
```

Compatibility alias:

```text
opencrab <same-command>
```

---

## Development

```bash
make dev-install
make seed
make status
make test-py312
make verify-intelligence
make dogfood-mcp
make lint
make format
```

Cross-platform examples above assume `python` resolves to a supported interpreter.

Canonical Windows verification:

```bash
py -3.12 scripts/verify_repo_intelligence.py
py -3.12 -m pytest tests/test_cli.py tests/test_mcp.py tests/test_stores.py
py -3.12 scripts/dogfood_mcp.py
```

To refresh checked-in MCP session evidence:

```bash
py -3.12 scripts/dogfood_mcp.py --transcript-dir docs/evidence/agent_sessions/latest
```

## Compatibility Note

MCP tool names remain aligned with OpenCrab for compatibility.

User-facing MCP payload labels were intentionally modernized to reflect the local runtime:

- `stores.neo4j` -> `stores.graph`
- `stores.mongodb` -> `stores.documents`
- `stores.postgres` -> `stores.registry`
- `stores.chromadb` -> `stores.vectors`

This is an intentional breaking change in payload shape, not a signal that legacy service-backed databases still exist.

### Project structure

```text
opencrab/
├── grammar/          # MetaOntology grammar and validation
├── stores/           # LadybugDB, DuckDB, ChromaDB adapters
├── ontology/         # Builder, query, ReBAC, impact, extractor
└── mcp/              # MCP server and tool definitions
tests/                # Local-first test suite
scripts/              # Seed script
```

---

## License

MIT
