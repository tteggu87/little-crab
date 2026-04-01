# little-crab AGENTS

little-crab is the local-first fork of OpenCrab. Treat the project's main identity as: preserve the OpenCrab grammar, validator, MCP tool surface, and agentic ontology workflow, while stripping away server-backed database operational weight.

## Working Style

- Keep `little-crab` local-first.
- Preserve the OpenCrab grammar, validator behavior, MCP tool names, and agentic ontology loop.
- Prefer narrow, explicit changes over broad redesigns.
- Treat documentation drift as a bug, not a cleanup someday task.

## Repository Rules

- Canonical package entrypoints live in [pyproject.toml](pyproject.toml).
- Canonical CLI implementation lives in [opencrab/cli.py](opencrab/cli.py).
- Canonical MCP server lives in [opencrab/mcp/server.py](opencrab/mcp/server.py).
- Canonical grammar lives in [opencrab/grammar/manifest.py](opencrab/grammar/manifest.py) and [opencrab/grammar/validator.py](opencrab/grammar/validator.py).
- Canonical local runtime is `LadybugDB + DuckDB + embedded ChromaDB`.
- Do not reintroduce Neo4j, MongoDB, PostgreSQL, or Docker-first paths without an explicit architecture decision.
- The Python module namespace remains `opencrab` for compatibility even though the package/project name is `little-crab`.

## Documentation Rules

- Keep these as current canonical docs:
  - [docs/README.md](docs/README.md)
  - [docs/CURRENT_STATE.md](docs/CURRENT_STATE.md)
  - [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
  - [docs/LAYERS.md](docs/LAYERS.md)
  - [docs/SKILLS_INTEGRATION.md](docs/SKILLS_INTEGRATION.md)
  - [docs/ROADMAP.md](docs/ROADMAP.md)
  - [docs/IMPACT_SUMMARY.md](docs/IMPACT_SUMMARY.md)
- Keep lightweight repository intelligence current under [intelligence](intelligence).
- Do not silently repurpose design notes as source of truth.
- Existing design notes in `docs/*.md` with dated filenames are supporting context unless a canonical doc says otherwise.

## Definition Of Done

- Code changes align with the current local-only runtime.
- Relevant docs are updated in the same task.
- Relevant intelligence files are updated in the same task.
- `pytest` coverage for touched paths is run or the gap is explicitly called out.
- Any intentional legacy or compatibility exception is documented explicitly.
