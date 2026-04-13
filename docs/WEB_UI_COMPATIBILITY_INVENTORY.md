---
status: Active
source_of_truth: Yes
last_updated: 2026-04-13
superseded_by: N/A
---

# Web UI Maximal-Reuse Compatibility Inventory

## Purpose

This document inventories the upstream OpenCrab web product lane so little-crab can reuse as much UI code as possible without importing hosted or server-first assumptions into the core local-first runtime.

It completes the `Lane F — Web product surfaces` next action from [UPSTREAM_BACKLOG.md](UPSTREAM_BACKLOG.md): classify the current upstream `apps/web` + `apps/api` + `server` surface into:

- `Nearly-as-is`
- `Shim-needed`
- `Exclude`

## Upstream slice reviewed

Primary upstream reference: `AlexAI-MCP/OpenCrab`

Reviewed commits / signals:

- `8ff9ec5` — SaaS web layer introduction
- `f1738b8` — web app cleanup
- `036402f` — dependency cleanup
- current `main` state through `dcacc58`

Reviewed upstream paths:

- `apps/web/*`
- `apps/api/*`
- `server/api.py`

## Compatibility summary

| Category | Meaning for little-crab |
| --- | --- |
| Nearly-as-is | Can be copied with minimal or no semantic change because it is mostly presentation shell or neutral bootstrapping. |
| Shim-needed | Worth reusing, but only after adapting route names, auth expectations, storage assumptions, or local-first terminology. |
| Exclude | Do not import into the first local UI boot path because it would thicken the fork or reintroduce hosted-product assumptions. |

## Nearly-as-is

These files are mostly UI shell or packaging scaffolding and can be reused with little semantic risk.

| Upstream file(s) | Why reuse is cheap | little-crab note |
| --- | --- | --- |
| `apps/web/app/layout.tsx` | Thin metadata + root shell only. | Rename product copy from `OpenCrab` to `little-crab` during import. |
| `apps/web/app/page.tsx` | Pure redirect to the dashboard route. | Safe if the local UI keeps `/dashboard` as the entry route. |
| `apps/web/app/globals.css` | Mostly visual tokens and generic panel/button/input styling. | Keep ontology-space color tokens; adjust brand copy only. |
| `apps/web/components/GraphView.tsx` | Pure client-side D3 rendering of node/edge payloads. | Reuse directly once the API payload keeps `{id, space, node_type, degree}` and `{from_id, to_id, relation}`. |
| `apps/web/next.config.mjs`, `postcss.config.js`, `tailwind.config.ts`, `tsconfig.json`, `next-env.d.ts` | Standard Next/Tailwind setup. | Copy as the initial frontend skeleton. |
| `server/api.py` | Tiny deployment adapter that exposes `apps.api.main:app` through `server.api:app`. | Keep the pattern if a local FastAPI sidecar is introduced. |

## Shim-needed

These areas are good maximal-reuse candidates, but only behind a local-first compatibility layer.

| Upstream file(s) | Upstream assumption to adapt | Required shim / reinterpretation |
| --- | --- | --- |
| `apps/web/lib/api.ts` | Hard-coded hosted default (`https://opencrabback.up.railway.app`) and bearer-token header on every request. | Point default base URL to a local sidecar, make auth optional or local-only, and map routes onto little-crab-specific endpoints. |
| `apps/web/app/dashboard/page.tsx` | Blocks useful graph loading behind API-key entry and assumes periodic hosted polling. | Replace API-key gate with local connectivity state; keep the dashboard layout and refresh loop. |
| `apps/web/components/FileExplorer.tsx` | Uses PARA-like folder heuristics and `source_id` conventions that are not canonical in little-crab. | Rebuild grouping around source ids, evidence docs, and ontology spaces rather than PARA folders. |
| `apps/web/components/RightPanel.tsx` | Couples the UI to hosted query/ingest flows, free-form source ids, and current upstream wording. | Keep the tabs and control layout, but retarget actions to local read routes first and defer writes behind explicit local workflows. |
| `apps/web/package.json` | Assumes a standalone Next app install flow and keeps `next lint`/lockfile decisions tied to the upstream repo shape. | Reuse dependency set, but establish little-crab-owned package manager and workspace rules before import. |
| `apps/web/Dockerfile` | Good structure, but assumes the web app is shipped as a containerized service. | Keep only if local sidecar + web packaging becomes a supported optional distribution path. |
| `apps/api/main.py` | Assumes a hosted FastAPI product API with bearer auth, usage metering, free/pro tier limits, and remote HTTP consumers. | Reinterpret as a local read-mostly visualization sidecar that wraps existing little-crab runtime services. |
| `apps/api/requirements.txt` | Introduces FastAPI/uvicorn/httpx stack not currently in little-crab package metadata. | Move to an optional extra or separate app dependency set so the core runtime stays lean. |
| `apps/api/Dockerfile` | Assumes containerized remote serving as a default product path. | Keep only as an optional packaging artifact after the local sidecar exists. |

## Route compatibility map

This is the narrowest route-level reinterpretation that preserves the upstream dashboard flow while keeping little-crab local-first.

| Upstream route / expectation | Compatibility status | little-crab target | Notes |
| --- | --- | --- | --- |
| `GET /api/status` | Nearly-as-is | `GET /api/status` | Keep the route; return local store health instead of hosted service metadata. |
| `GET /api/nodes` | Shim-needed | `GET /api/nodes` | Keep the route name, but build payloads from Ladybug-backed graph reads and current ontology-space labels. |
| `GET /api/edges` | Shim-needed | `GET /api/edges` | Same route is fine if payload shape stays `{from_id,to_id,relation,from_space,to_space}`. |
| `POST /api/query` | Shim-needed | `POST /api/query` | Reuse route name, but wire it to little-crab's existing hybrid query/context pipeline rather than hosted product semantics. |
| `POST /api/ingest` | Defer after read path | optional later | Keep out of the first import pass unless a local-safe write UX is explicitly scoped. |
| `GET /api/usage` | Exclude | none in v1 | Product metering is not part of the local UI adoption goal. |
| bearer `Authorization` header on all requests | Exclude from v1 | optional local auth later | Do not make local graph inspection depend on remote-style credentials. |

## Exclude

These upstream behaviors should not be copied into the first little-crab UI adoption pass.

| Upstream behavior | Why it should be excluded |
| --- | --- |
| Railway-hosted default backend URL and deploy-first assumptions | little-crab's preserve set is local-first, not hosted-first. |
| API-key-in-localStorage as the default operator entry path | local operator UX should not require a hosted product credential ceremony just to inspect a local graph. |
| Free/pro/api tier limits, usage counters, and metering semantics in `apps/api/main.py` | These are productization concerns, not core local runtime requirements. |
| Remote-first write surface as the first UX milestone | The backlog calls for maximal UI reuse, not for importing a hosted write product before the read-only local boot path exists. |
| Container/remote deployment artifacts as mandatory runtime dependencies | Optional packaging is fine later, but it should not redefine the core repo or install path now. |

## File-by-file import recommendation

### `apps/web`

#### Reuse first

- keep the Next.js shell
- keep the dark ontology-workbench styling
- keep the D3 graph renderer
- keep the three-pane dashboard layout

#### Change on import

- rename product copy to little-crab
- change route client to local endpoints
- remove mandatory hosted auth flow
- regroup left navigation around local source/evidence organization
- downgrade ingest/query controls so they match current local runtime guarantees

### `apps/api`

#### Reuse first

- the FastAPI app shape
- the idea of explicit `status`, `nodes`, `edges`, and `query` endpoints for a local graph workbench
- the `server/api.py` adapter pattern

#### Change on import

- replace old store wiring assumptions with `make_runtime_services()` from little-crab
- trim productization concerns out of the first cut
- prefer read-only or read-mostly routes first
- map response naming to little-crab's local-role labels and current ontology semantics

### `server`

#### Reuse first

- tiny deployment adapter only

#### Change on import

- keep it optional
- do not let it imply that remote hosting is a new core requirement

## Minimal compatibility target

The smallest credible maximal-reuse target is:

1. import the upstream `apps/web` shell
2. keep `GraphView.tsx`, layout, global styles, and dashboard structure mostly intact
3. add a little-crab-specific API shim layer that serves:
   - graph status
   - graph nodes
   - graph edges
   - search/query results
   - node detail payloads
4. remove hosted auth, tiering, and metering from the first boot path
5. defer remote deployment packaging until after a near-stock local boot works

## Concrete next steps

### Step 1 — establish the local API shim boundary

Create a local visualization sidecar that exposes stable routes for the reused web app. Prefer route names that stay close to the existing upstream dashboard expectations, but keep the implementation backed by little-crab's current local runtime services.

Recommended first routes:

- `GET /api/status`
- `GET /api/nodes`
- `GET /api/edges`
- `POST /api/query`
- `GET /api/node/{id}`

### Step 2 — import the nearly-as-is web shell first

Copy the upstream web shell with the smallest possible diff:

- `app/layout.tsx`
- `app/page.tsx`
- `app/globals.css`
- `components/GraphView.tsx`
- baseline Next/Tailwind config files

Do not redesign the UI before the near-stock local boot path exists.

### Step 3 — add only the required UI shims

Apply narrow changes to:

- `lib/api.ts`
- `dashboard/page.tsx`
- `FileExplorer.tsx`
- `RightPanel.tsx`

Goal:

- local-first connectivity
- ontology-space-friendly grouping
- little-crab wording
- no hosted credential dependency for local inspection

### Step 4 — keep product-only concerns deferred

Do not import these into the first pass:

- hosted auth gating
- pricing/tier logic
- usage metering UX
- deploy-first Railway assumptions

### Step 5 — validate against the preserve set

Before landing any imported UI slice, verify that it does **not** change:

- local-first runtime as the default mode
- current MCP tool naming
- current CLI/MCP ontology semantics
- explicit backend divergence boundaries documented in [FORK_BOUNDARY.md](FORK_BOUNDARY.md)

## Decision

**Classification: `Reinterpret` with maximal reuse remains correct.**

The upstream web lane is reusable enough to justify importing the shell and renderer first, but only if little-crab inserts a thin local compatibility layer and refuses the hosted-product assumptions that currently sit behind `apps/api` and parts of the dashboard flow.
