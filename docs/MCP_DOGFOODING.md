---
status: Active
source_of_truth: Yes
last_updated: 2026-03-26
superseded_by: N/A
---

# MCP Dogfooding

## Purpose

This guide defines the canonical local dogfood path for little-crab's stdio MCP surface.

Use it when you want to prove that the project still delivers the OpenCrab-derived workflow:

- inspect grammar
- add partial ontology structure
- ingest and extract from local text
- query the graph
- run ReBAC, impact, and lever simulation

## Canonical Verification Commands

On this repository's Windows setup, the canonical commands are:

```bash
py -3.12 -m pytest tests/test_cli.py tests/test_mcp.py tests/test_stores.py
py -3.12 scripts/dogfood_mcp.py
py -3.12 scripts/dogfood_mcp.py --transcript-dir docs/evidence/agent_sessions/latest
```

`make test-py312` and `make dogfood-mcp` are thin wrappers for the same checks.

## Scenario Set

### Scenario 1: grammar -> node -> edge

Goal:
Confirm that an agent can inspect the grammar and extend the ontology without bypassing validation.

Expected MCP flow:

1. `initialize`
2. `tools/list`
3. `ontology_manifest`
4. `ontology_add_node`
5. `ontology_add_node`
6. `ontology_add_edge`

Success conditions:

- grammar is returned
- both nodes are created
- the edge is accepted only when the relation is grammar-valid

### Scenario 2: ingest -> extract -> query

Goal:
Confirm that local text can enter the embedded stores and become queryable through the agent-facing MCP surface.

Expected MCP flow:

1. `ontology_ingest`
2. `ontology_extract`
3. `ontology_query`

Success conditions:

- ingest writes to the embedded vector/document path
- extract adds at least a minimal node/edge set
- query returns at least one relevant result

### Scenario 3: rebac -> impact -> simulation

Goal:
Confirm that the analytical surfaces remain live after local writes.

Expected MCP flow:

1. `ontology_add_node`
2. `ontology_add_node`
3. `ontology_add_edge`
4. `ontology_rebac_check`
5. `ontology_add_node`
6. `ontology_add_node`
7. `ontology_add_edge`
8. `ontology_impact`
9. `ontology_lever_simulate`

Success conditions:

- ReBAC grants expected direct access
- impact returns triggered categories
- lever simulation returns predicted outcome changes

## Automation Entry Point

The repeatable local harness lives at:

- [scripts/dogfood_mcp.py](/C:/python_Github/playground/little-crab/scripts/dogfood_mcp.py)

By default the script creates a temporary `LOCAL_DATA_DIR`, runs all three scenarios, prints `PASS` or `FAIL`, and removes the temp directory unless `--keep-data-dir` is supplied.

If `--transcript-dir` is supplied, the script also writes sanitized JSON transcript files plus a Markdown summary that can be committed as agent-session evidence.

## Checked-In Evidence

Canonical evidence notes live at:

- [AGENT_SESSION_EVIDENCE.md](/C:/python_Github/playground/little-crab/docs/AGENT_SESSION_EVIDENCE.md)

Canonical session artifacts currently live under:

- [docs/evidence/agent_sessions/2026-03-26-canonical](/C:/python_Github/playground/little-crab/docs/evidence/agent_sessions/2026-03-26-canonical)

## Failure Signals

- no `initialize` response from the stdio server
- `tools/list` returns fewer than the expected ontology tools
- grammar-valid node/edge writes fail
- query returns no results after ingest/extract
- ReBAC does not grant expected direct access
- impact or simulation returns empty analytical output

## Notes

- This guide validates the current local-first runtime, not a future web app or visualization sidecar.
- Keep the scenarios narrow and deterministic.
- If a future skill, wrapper, or CI job automates these checks, link it here after it exists in code.
