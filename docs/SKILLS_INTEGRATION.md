---
status: Active
source_of_truth: Yes
last_updated: 2026-03-26
superseded_by: N/A
---

# Skills Integration

## Current Integration Surface

little-crab does not ship repo-local Codex skills. Its integration surface is the MCP toolset exposed by [opencrab/mcp/server.py](/C:/python_Github/playground/little-crab/opencrab/mcp/server.py) and [opencrab/mcp/tools.py](/C:/python_Github/playground/little-crab/opencrab/mcp/tools.py).

## Practical Use

- Agents connect over MCP stdio.
- Agents use `ontology_manifest` first to inspect grammar.
- Agents then use:
  - `ontology_ingest`
  - `ontology_extract`
  - `ontology_add_node`
  - `ontology_add_edge`
  - `ontology_query`
  - `ontology_rebac_check`
  - `ontology_impact`
  - `ontology_lever_simulate`

## Repository-Side Guidance

- If a future skill or wrapper is added, document it here only after it exists in code.
- Do not present external orchestration ideas as built-in capabilities.
- The existing Polaris adaptation note is design context, not an integrated feature yet.

## Dogfood Guidance

The canonical local dogfood guide for this MCP surface lives at:

- [MCP_DOGFOODING.md](/C:/python_Github/playground/little-crab/docs/MCP_DOGFOODING.md)

Use it to validate the real agent workflow:

- grammar inspection
- local ingest and extraction
- graph extension
- query
- ReBAC
- impact
- lever simulation
