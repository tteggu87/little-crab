# Polaris Adaptation For Little-Crab

Date: 2026-03-26
Status: proposed
Decision: use Polaris as the primary visualization shell for little-crab; absorb only selected nebula ideas from langent in a later phase.

## 3-line decision

1. Primary visualization base: Polaris.
2. Langent is a reference implementation for nebula-style affordances, not the runtime or UI base.
3. Build a little-crab-specific projection/API layer and keep nebula visualization as an optional phase-2 mode.

## Why this direction

OpenCrab/little-crab's core value is not "pretty graph rendering." Its value is:

- the 9-space grammar
- the relation validator
- the MCP tool surface
- the agentic loop that can fill gaps conservatively over time

That means the default visualization should optimize for:

- ontology operability
- provenance visibility
- relation readability
- search -> inspect -> act workflows

Polaris matches that better than langent.

## Final recommendation

Do this:

- keep Polaris as the main graph workbench
- adapt Polaris types and panels to little-crab's ontology model
- add a small little-crab visualization sidecar API
- optionally add a nebula route later using langent-inspired ideas

Do not do this:

- do not adopt langent as the main UI/runtime
- do not import langent's Neo4j/LangGraph/server assumptions into little-crab
- do not make 3D nebula the default view

## What already exists

### In little-crab / OpenCrab

- ontology grammar: `opencrab/grammar/manifest.py`
- validator: `opencrab/grammar/validator.py`
- graph/query/impact/rebac engines: `opencrab/ontology/`
- local-first stores: `opencrab/stores/`
- MCP tool surface: `opencrab/mcp/tools.py`

### In Polaris

- fixed-shell graph workbench
- Sigma + Graphology graph rendering
- search drawer / inspector drawer / left rail
- simple read-only API contract

Relevant source:

- `C:\python_Github\ontol-codex\kuzu2\zk_graph_deploy_with_agent_20260309_170133\apps\polaris-route\src\App.tsx`
- `C:\python_Github\ontol-codex\kuzu2\zk_graph_deploy_with_agent_20260309_170133\apps\polaris-route\src\components\GraphCanvas.tsx`
- `C:\python_Github\ontol-codex\kuzu2\zk_graph_deploy_with_agent_20260309_170133\src\ontology2\viz\api.py`
- `C:\python_Github\ontol-codex\kuzu2\zk_graph_deploy_with_agent_20260309_170133\src\ontology2\viz\projection.py`

### In langent

- 3D nebula view
- search highlight + fly-to behavior
- vector-point + graph-node cross-link idea
- live update / websocket idea

Relevant source:

- `C:\python_Github\Agent_skill\copy skill\langent\langent\visualizer\app.js`
- `C:\python_Github\Agent_skill\copy skill\langent\langent\server\api.py`
- `C:\python_Github\Agent_skill\copy skill\langent\langent\brain.py`

## Not in scope

- replacing little-crab's ontology runtime with langent
- making Polaris write directly to ontology stores in v1
- full 3D renderer in phase 1
- websocket/live streaming in phase 1
- multi-pane dashboard redesign

## Target UX

Phase 1 should support this loop:

1. open graph
2. filter by ontology spaces
3. search by node label / id / relation / source path
4. click node
5. inspect node properties, provenance, neighbors, impacts, access hints
6. jump to related nodes
7. optionally open source text / evidence excerpts

Phase 2 can add:

1. nebula view
2. chunk/vector density view
3. evidence-to-concept cross-links
4. live refresh after ingest/add-node/add-edge

## Architecture

```text
little-crab runtime
  -> grammar / validator / stores / ontology engines
  -> viz projection layer
  -> FastAPI read-only sidecar
  -> Polaris frontend

optional phase 2:
  -> vector position projector
  -> nebula route
```

```text
MCP / CLI / local store writes
  -> little-crab graph + duckdb + chroma
  -> projection builder
  -> /api/littlecrab/*
  -> Polaris UI
```

## Data model mapping

Polaris currently expects node types like:

- `source`
- `document`
- `page`
- `entity`
- `process`

Little-crab should instead expose:

- `subject`
- `resource`
- `evidence`
- `concept`
- `claim`
- `community`
- `outcome`
- `lever`
- `policy`

Recommended mapping rule:

- `node_type` in the UI should be the ontology `space`
- original ontology `node_type` should be shown as a secondary label

Example:

```json
{
  "id": "lever-cache-ttl",
  "label": "Cache TTL",
  "node_type": "lever",
  "subtitle": "Lever"
}
```

This keeps filtering simple and aligned with the OpenCrab grammar.

## Little-crab API contract

Create a read-only sidecar API similar to Polaris, but with little-crab semantics.

### `GET /api/littlecrab/meta`

Returns:

- app metadata
- storage mode
- grammar summary
- graph counts
- optional recommended actions

### `GET /api/littlecrab/graph`

Returns:

- graph nodes
- graph edges
- node/edge counts

### `GET /api/littlecrab/source-tree`

Returns:

- source/evidence-oriented explorer tree

For little-crab this should be grouped as:

- sources
- evidence documents
- optionally claim/concept references

### `GET /api/littlecrab/node/{node_id}`

Returns detail payload:

- node id
- space
- ontology node_type
- properties
- provenance
- related nodes
- supporting evidence previews
- triggered impact summary if available
- access hints if relevant

### `GET /api/littlecrab/processes`

Optional in v1.

Recommended reinterpretation:

- not OS processes
- instead "analysis cards" or "operations"
- examples: `impact`, `rebac`, `lever simulation`

This endpoint may be omitted in the first cut if it complicates the UI.

### `GET /api/littlecrab/search?q=...`

Returns:

- matched nodes
- label / subtitle / node_type
- maybe source_path and snippet

## File-by-file implementation plan

### Phase 1A: backend projection and API

Add:

- `C:\python_Github\playground\OpenCrab\opencrab\viz\__init__.py`
- `C:\python_Github\playground\OpenCrab\opencrab\viz\projection.py`
- `C:\python_Github\playground\OpenCrab\opencrab\viz\api.py`

Responsibilities:

- `projection.py`
  - build graph payload from Ladybug + DuckDB + Chroma-backed little-crab runtime
  - map ontology nodes to Polaris-compatible UI nodes
  - map ontology edges to UI edges
  - build search index
  - build node detail payload
  - optionally build source/evidence tree

- `api.py`
  - expose `create_littlecrab_app()`
  - provide `/api/littlecrab/meta`
  - provide `/api/littlecrab/graph`
  - provide `/api/littlecrab/source-tree`
  - provide `/api/littlecrab/node/{node_id}`
  - provide `/api/littlecrab/search`

Recommended rule:

- keep this layer read-only in v1
- write actions continue to happen through MCP / CLI

### Phase 1B: Polaris frontend port

Add:

- `C:\python_Github\playground\OpenCrab\apps\polaris-little-crab\`

Copy/adapt from:

- `C:\python_Github\ontol-codex\kuzu2\zk_graph_deploy_with_agent_20260309_170133\apps\polaris-route\`

Required frontend files:

- `apps/polaris-little-crab/package.json`
- `apps/polaris-little-crab/vite.config.ts`
- `apps/polaris-little-crab/src/main.tsx`
- `apps/polaris-little-crab/src/App.tsx`
- `apps/polaris-little-crab/src/api.ts`
- `apps/polaris-little-crab/src/types.ts`
- `apps/polaris-little-crab/src/view-model.ts`
- `apps/polaris-little-crab/src/components/GraphCanvas.tsx`
- `apps/polaris-little-crab/src/components/LeftSidebar.tsx`
- `apps/polaris-little-crab/src/components/InspectorPanel.tsx`
- `apps/polaris-little-crab/src/styles.css`

### Phase 1C: little-crab-specific UI adaptation

Modify these behaviors compared with Polaris:

- left rail filters should use the 9 ontology spaces
- inspector should show:
  - `space`
  - `node_type`
  - `properties`
  - provenance / source id
  - evidence previews
  - relation list
  - neighboring nodes
  - impact summary
  - rebac hints when relevant

- tree explorer should prefer:
  - sources
  - evidence
  - optionally documents by source path

- process tab should become:
  - `analysis`
  - or be removed in v1

## Concrete file adaptation notes

### `apps/polaris-little-crab/src/types.ts`

Replace Polaris-specific concepts with little-crab types.

Keep:

- `PolarisNode`-like shape
- `PolarisEdge`-like shape
- `DetailPayload`

Rename if desired, but keep payload structure stable enough to reuse components.

### `apps/polaris-little-crab/src/api.ts`

Change routes:

- `/api/polaris/meta` -> `/api/littlecrab/meta`
- `/api/polaris/graph` -> `/api/littlecrab/graph`
- `/api/polaris/source-tree` -> `/api/littlecrab/source-tree`
- `/api/polaris/source/{id}` -> `/api/littlecrab/node/{id}`
- `/api/polaris/search` -> `/api/littlecrab/search`

### `apps/polaris-little-crab/src/components/LeftSidebar.tsx`

Change fixed filters from:

- `source/document/page/entity/process`

To:

- `subject/resource/evidence/concept/claim/community/outcome/lever/policy`

### `apps/polaris-little-crab/src/components/InspectorPanel.tsx`

Strip kuzu2-specific fields like:

- `note_role`
- `generation_provenance`
- `member_ids`

Replace with little-crab fields:

- `space`
- `node_type`
- `source_id`
- `supporting_evidence`
- `graph_neighbors`
- `impact`
- `rebac`

### `opencrab/viz/projection.py`

This is the main seam.

It should:

- read nodes from graph/doc store
- create a normalized UI graph
- preserve the ontology space as the primary visible type
- keep node ids stable and human-debuggable

## Langent ideas to absorb later

Absorb:

- nebula point cloud from vector positions
- search hit highlighting
- fly-to focused camera behavior
- vector-point to ontology-node cross-links

Do not absorb:

- langent runtime orchestration
- langgraph coupling
- neo4j dependency
- workspace-specific ingest assumptions
- langent MCP surface

## Phase 2: nebula mode

If phase 1 lands well, add:

- `C:\python_Github\playground\OpenCrab\apps\nebula-little-crab\`
  - or a `/nebula` route under the same frontend

Backend additions:

- `GET /api/littlecrab/nebula`
- `GET /api/littlecrab/nebula/search`

Inputs:

- Chroma embeddings
- optional UMAP or deterministic projection
- optional chunk-to-node link metadata

UI behavior:

- keep graph workbench as default
- nebula is an optional secondary mode

## Testing plan

### Backend tests

Add:

- `C:\python_Github\playground\OpenCrab\tests\test_viz_projection.py`
- `C:\python_Github\playground\OpenCrab\tests\test_viz_api.py`

Test:

- graph payload is non-empty after seeded data
- every node exposes `id`, `label`, `node_type`
- every edge references valid node ids
- search returns stable results
- detail endpoint returns provenance/evidence structure

### Frontend tests

For `apps/polaris-little-crab`:

- smoke render
- graph loads from API
- filter by ontology space
- search opens result
- inspector renders node properties

## Risks

1. Polaris inspector is still biased toward kuzu2 payloads.
   Fix: adapt `DetailPayload` and simplify early.

2. Little-crab may not yet have a strong source-tree concept.
   Fix: treat source tree as optional; evidence list is enough for v1.

3. Nebula can distract from ontology operability.
   Fix: keep nebula behind phase 2 and never make it the default.

## Recommended delivery order

1. add `opencrab/viz/projection.py`
2. add `opencrab/viz/api.py`
3. port Polaris into `apps/polaris-little-crab`
4. adapt filters + inspector to 9-space ontology
5. add backend/frontend tests
6. only then evaluate nebula mode

## One-line implementation verdict

Build little-crab visualization on Polaris now, and treat langent as a source of secondary visualization ideas rather than as the base product.
