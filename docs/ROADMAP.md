---
status: Active
source_of_truth: Yes
last_updated: 2026-03-27
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

## Likely Next Work

1. Polaris-based visualization sidecar for little-crab.
2. Stronger repo-level docs portal and docs classification.
3. Optional module renaming from `opencrab` to `little_crab` if compatibility cost becomes acceptable.

Any Polaris-based sidecar should be evaluated against those flexibility goals, not only against visual polish.

## Explicitly Not Committed Yet

- LanceDB replacement for ChromaDB
- built-in web app
- new manifest-driven execution runtime
- reintroduction of service-backed DB infrastructure
