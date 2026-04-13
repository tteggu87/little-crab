---
status: Active
source_of_truth: Yes
last_updated: 2026-04-13
superseded_by: N/A
---

# MCP / CLI Protocol Compatibility Inventory

## Purpose

This document records the concrete Lane B inventory for upstream remote/API
transport changes and maps them onto little-crab's local-first MCP + CLI
runtime.

It is intentionally scoped to protocol surfaces, not to upstream product UI.

## Scope Reviewed

### little-crab local sources

- `opencrab/mcp/server.py`
- `opencrab/cli.py`
- `tests/test_mcp.py`
- `tests/test_cli.py`

### upstream OpenCrab sources

- current repo tree for `opencrab-ai-com/opencrab`
- `lib/server/api-route.ts`
- `app/api/codex/browser-mcp/route.ts`
- `app/api/runtime/readiness/route.ts`
- `lib/codex/browser-session.ts`
- `lib/resources/opencrab-api.ts`
- `lib/resources/opencrab-api-types.ts`

Reference URLs reviewed:

- `https://github.com/opencrab-ai-com/opencrab`
- `https://raw.githubusercontent.com/opencrab-ai-com/opencrab/main/lib/server/api-route.ts`
- `https://raw.githubusercontent.com/opencrab-ai-com/opencrab/main/app/api/codex/browser-mcp/route.ts`
- `https://raw.githubusercontent.com/opencrab-ai-com/opencrab/main/app/api/runtime/readiness/route.ts`
- `https://raw.githubusercontent.com/opencrab-ai-com/opencrab/main/lib/codex/browser-session.ts`
- `https://raw.githubusercontent.com/opencrab-ai-com/opencrab/main/lib/resources/opencrab-api.ts`
- `https://raw.githubusercontent.com/opencrab-ai-com/opencrab/main/lib/resources/opencrab-api-types.ts`

## Upstream Path Reality Check

The mailbox assignment named upstream `apps/api/main.py` and `server/api.py`.
On current upstream `main`, those exact paths do **not** exist.

Current upstream equivalents are:

- `app/api/**/route.ts` for HTTP route handlers
- `lib/server/api-route.ts` for shared JSON/error helpers
- `lib/codex/browser-session.ts` for the MCP-over-HTTP browser bridge

This matters because the current upstream transport lane is no longer a Python
API server. It is a Next.js app-router HTTP surface with a browser-MCP bridge.

## Current little-crab Baseline

little-crab already reinterpreted a meaningful subset of MCP protocol changes
into the local stdio server:

- negotiated MCP protocol versions
- `notifications/initialized`
- `resources/list`
- `resources/templates/list`
- batched JSON-RPC request handling
- `ping`
- machine-readable MCP tests for the above behavior

Relevant local evidence:

- `opencrab/mcp/server.py`
- `tests/test_mcp.py`
- `docs/CURRENT_STATE.md`

little-crab intentionally does **not** ship:

- remote HTTP MCP transport
- browser-session bridge management
- web-route error envelopes
- product-facing REST/route APIs for conversations, channels, tasks, or auth

That absence is aligned with the preserve set in `docs/FORK_BOUNDARY.md`.

## Delta Inventory

### 1. MCP handshake + baseline protocol coverage

- **Upstream shape**
  - upstream browser bridge uses the official MCP SDK
  - transport is `WebStandardStreamableHTTPServerTransport`
  - tool listing and tool calls are exposed over HTTP
- **little-crab classification**
  - **Adopt / Reinterpret**
- **Current little-crab state**
  - already adopted for stdio JSON-RPC:
    - negotiated protocol versions
    - `notifications/initialized`
    - `resources/list`
    - `resources/templates/list`
    - batch request handling
    - `ping`
- **Decision**
  - keep stdio as the canonical local transport
  - continue matching MCP host expectations at the protocol level
  - do not add HTTP MCP transport by default
- **Reason**
  - protocol compatibility helps future syncability
  - shipping an HTTP transport would widen runtime scope beyond the preserve set

### 2. Streamable HTTP transport for MCP

- **Upstream shape**
  - browser-facing MCP bridge mounted at `/api/codex/browser-mcp`
  - HTTP server transport wraps an in-process MCP server and proxies to a live browser bridge
- **little-crab classification**
  - **Reinterpret / Defer**
- **Decision**
  - do not port the HTTP transport surface into core little-crab now
  - preserve the idea of a transport boundary so a sidecar can be added later if needed
- **Reason**
  - the transport abstraction is useful
  - the shipped remote/browser surface is product-specific and server-like
- **Boundary**
  - adopt the architectural lesson: keep MCP request handling isolated from transport
  - defer any HTTP exposure until there is a concrete local-sidecar use case

### 3. Shared API response helpers and error envelopes

- **Upstream shape**
  - `lib/server/api-route.ts` centralizes:
    - JSON responses
    - no-store headers
    - request IDs
    - normalized error/status/code payloads
- **little-crab classification**
  - **Reinterpret**
- **Decision**
  - do not import the HTTP helper layer directly
  - treat it as a model for future machine-readable CLI/MCP diagnostics
- **Reason**
  - the underlying value is structured diagnostics, not the web framework itself
- **Near-term reuse**
  - request/error normalization ideas can inform future CLI `--json-output` and MCP error payload consistency

### 4. Runtime readiness + connection-state APIs

- **Upstream shape**
  - HTTP endpoints such as `/api/runtime/readiness` and `/api/runtime/connection-state`
  - typed JSON contracts in `lib/resources/opencrab-api-types.ts`
- **little-crab classification**
  - **Reinterpret**
- **Current little-crab state**
  - `littlecrab status`
  - `littlecrab doctor`
  - JSON output mode for doctor
- **Decision**
  - keep readiness reporting CLI-first
  - standardize more machine-readable readiness summaries where that helps orchestration
- **Reason**
  - the operator need is real
  - the HTTP endpoint surface is not required for local-first core runtime

### 5. Typed client API surface for product routes

- **Upstream shape**
  - `lib/resources/opencrab-api.ts` provides a typed client for many `/api/*` endpoints
  - covers conversations, tasks, projects, browser session status, ChatGPT connection, uploads, and more
- **little-crab classification**
  - **Reject for core / Reinterpret at boundary**
- **Decision**
  - do not port this app-product API layer into core little-crab
  - only reuse shapes when they clarify a local operator contract already needed
- **Reason**
  - this is a product/web client surface, not a core ontology runtime requirement

### 6. Browser bridge and remote session lifecycle

- **Upstream shape**
  - `lib/codex/browser-session.ts` manages:
    - Chrome availability
    - browser session warmup
    - managed/current browser modes
    - MCP proxying to browser tools
- **little-crab classification**
  - **Defer**
- **Decision**
  - do not import browser lifecycle management into little-crab core
- **Reason**
  - valuable upstream product capability
  - outside little-crab's current ontology-runtime mission

### 7. CLI compatibility implications

- **Upstream shape**
  - upstream product routes expose readiness/session state over HTTP
  - upstream app surface can consume typed JSON status directly
- **little-crab classification**
  - **Adopt selectively**
- **Decision**
  - keep expanding structured CLI output where it reduces orchestration friction
  - preserve `littlecrab serve` as stdio MCP entrypoint
- **Reason**
  - this improves automation without importing remote runtime obligations

## Adopt / Reinterpret / Defer / Reject Summary

### Adopt

- continue protocol-level MCP host compatibility in stdio
- preserve transport-agnostic internal thinking where feasible
- expand machine-readable CLI/runtime summaries when bounded and local-first

### Reinterpret

- shared response/error normalization concepts
- readiness/connection-state reporting
- transport abstraction lessons without shipping HTTP transport

### Defer

- streamable HTTP MCP serving
- browser-session lifecycle management
- browser-bridge operational flows

### Reject For Core

- upstream product REST/client surface as a direct import target
- web-first route proliferation inside little-crab core

## Concrete Reuse Boundary

### Nearly reusable now

- MCP protocol expectation set
- structured readiness/diagnostic thinking
- transport-boundary discipline

### Reusable only behind a shim

- upstream error envelope conventions
- readiness/status payload shapes
- any future sidecar HTTP bridge layered on top of the existing stdio runtime

### Exclude from core little-crab

- `/api/*` product routes unrelated to ontology runtime
- browser-connection orchestration
- product auth/channel/upload/task web APIs

## Recommended Next Actions

1. keep Lane B docs-only for now; no core runtime expansion required yet
2. in Lane D, standardize one additional machine-readable CLI/runtime summary beyond extractor diagnostics
3. if a future local sidecar is needed, build it as an adapter over current stdio MCP rather than by replacing the current server
4. treat current upstream `app/api/**` + `lib/server/api-route.ts` as structural references, not direct merge targets

## Outcome

Lane B now has a concrete policy:

- **Adopt**
  - MCP protocol parity at the stdio boundary
  - more structured local diagnostics where useful
- **Reinterpret**
  - transport and error-envelope ideas
- **Defer**
  - remote/browser HTTP MCP bridge
- **Reject for core**
  - broad upstream product API surfaces
