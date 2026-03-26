# little-crab

[한국어 README](C:/python_Github/playground/little-crab/README.ko.md)

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

### 6. Connect from Codex MCP

Windows repo-local example:

```bash
codex mcp add little-crab ^
  --env PYTHONPATH=C:\path\to\little-crab ^
  --env STORAGE_MODE=local ^
  --env LOCAL_DATA_DIR=C:\path\to\little-crab\opencrab_data ^
  --env CHROMA_COLLECTION=little_crab_vectors ^
  --env MCP_SERVER_NAME=little-crab ^
  --env MCP_SERVER_VERSION=0.1.0 ^
  --env LOG_LEVEL=WARNING ^
  -- py -3.12 -m opencrab.cli serve
```

Then verify:

```bash
codex mcp list
```

Open a new Codex session after registration so the new MCP server is visible to the agent.

### 7. Connect from Claude Code MCP

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

## Recommended Workspace Layout

Keep runtime data separate from source material.

```text
your-project/
├── knowledge/
│   ├── inbox/        # raw notes, docs, reports, transcripts
│   ├── curated/      # cleaned or important reference docs
│   └── exports/      # optional generated summaries or extracts
├── opencrab_data/    # local runtime data created by little-crab
└── ...
```

Guidance:

- Put files you want the agent to learn from under `knowledge/inbox/` or `knowledge/curated/`.
- Do not manually edit `opencrab_data/`; it is runtime state, not source material.
- Prefer `.md`, `.txt`, `.py`, and short plain-text documents when starting out.

## Loading Material

For batch ingestion from disk:

```bash
little-crab ingest ./knowledge/inbox -r
little-crab ingest ./knowledge/curated -r
```

For agent-driven work over MCP:

- Ask the agent to read one or more files.
- Ask it to call `ontology_ingest` for semantic retrieval.
- Ask it to call `ontology_extract` if you want bootstrap nodes/edges.
- Ask it to call `ontology_query`, `ontology_rebac_check`, `ontology_impact`, or `ontology_lever_simulate` for follow-up analysis.

## What To Ask The Agent

Good starter requests:

- `먼저 ontology_manifest로 문법을 보여주고, 이 저장소에 맞는 공간 구성을 설명해줘.`
- `knowledge/inbox 폴더 문서들을 읽고 중요한 텍스트를 ontology_ingest 해줘.`
- `같은 문서들에서 concept, claim, evidence를 ontology_extract로 부트스트랩해줘.`
- `cache ttl, reliability, incident report 관련 내용을 ontology_query로 찾아줘.`
- `Alice가 events-dataset을 볼 수 있는지 ontology_rebac_check로 검사해줘.`
- `cache-ttl-lever를 올렸을 때 outcome 영향이 어떤지 ontology_lever_simulate로 보여줘.`
- `새 문서가 들어오면 기존 claim과 충돌하는지 확인해줘.`

Useful prompt pattern:

```text
1. 먼저 ontology_manifest로 현재 문법을 확인해.
2. knowledge/inbox 아래 문서 중 관련 있는 것만 읽어.
3. 중요한 본문은 ontology_ingest 해.
4. 필요한 경우 ontology_extract로 부트스트랩해.
5. 마지막에는 ontology_query 또는 impact/rebac/simulation으로 답을 정리해.
```

## Typical Workflow

1. Put raw material into `knowledge/inbox/`.
2. Connect Codex or Claude Code to little-crab over MCP.
3. Ask the agent to inspect the grammar with `ontology_manifest`.
4. Ingest or extract from the material.
5. Query the graph and vectors.
6. Add or refine nodes/edges as the ontology grows.
7. Use ReBAC, impact, and lever simulation when you need analysis instead of retrieval.

For a more detailed usage guide, see [docs/USAGE_GUIDE.md](/C:/python_Github/playground/little-crab/docs/USAGE_GUIDE.md).

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
