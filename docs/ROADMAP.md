---
status: Active
source_of_truth: Yes
last_updated: 2026-04-13
superseded_by: N/A
---

# Roadmap

## Near Term

1. Keep the local-only runtime stable and dogfoodable.
2. Maintain docs and intelligence artifacts alongside runtime changes.
3. Validate MCP workflows against real agent sessions.
4. Make OpenCrab flexibility preservation explicit in new read models and UX work:
   - keep partial knowledge visible
   - avoid ASCII-only query assumptions
   - preserve multi-hop provenance explanation
5. Stabilize the read-only agent context pipeline so agents consume one derived context contract without introducing a second SSOT.
6. Reposition little-crab as a thin backend/profile fork so upstream OpenCrab trajectory can be reused more cheaply:
   - maximize reuse of grammar, ontology semantics, and MCP-facing contracts
   - keep backend divergence explicit in local-first store/profile layers
   - avoid widening the core repo with upstream product surfaces that are not required for local-first runtime goals

## Likely Next Work

1. Continue the first-pass local operator web shell and compatibility shim from the upstream web lane.
2. Stronger repo-level docs portal and docs classification.
3. Optional module renaming from `opencrab` to `little_crab` if compatibility cost becomes acceptable.
4. Upstream extractor/intelligence review as the first deliberate trajectory catch-up lane.
5. Continued thinning of high-conflict coordinator files:
   - `opencrab/cli.py`
   - `opencrab/mcp/tools.py`
   - `opencrab/config.py`
   - `opencrab/stores/factory.py`
6. Phase 3 adoption review complete; next aligned lane is automation-ready outputs and explicit diagnostics.
7. Maintain an explicit upstream catch-up backlog so adoption proceeds one lane at a time instead of through broad merge attempts.

Any Polaris-based sidecar should be evaluated against those flexibility goals, not only against visual polish.

## Explicitly Not Committed Yet

- LanceDB replacement for ChromaDB
- built-in web app
- new manifest-driven execution runtime
- reintroduction of service-backed DB infrastructure
- wholesale import of upstream web/app/harness surfaces into core little-crab
