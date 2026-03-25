# LanceDB Evaluation for Embedded OpenCrab

Date: 2026-03-26

## Decision

Keep `ChromaDB` for phase 1 of the embedded/serverless refactor.

Do **not** replace the vector layer with LanceDB in this refactor wave.

## Baseline

The embedded runtime now uses:

- `LadybugDB` for graph traversal
- `DuckDB` for docs, registry, policies, impacts, and simulations
- embedded `ChromaDB PersistentClient` for vectors

This means the original Chroma HTTP server dependency is already gone in local mode.

## Why Keep Chroma

1. The main simplification target was external services, not vector semantics.
   - That target is already met because local mode uses embedded Chroma.

2. OpenCrab already has a working Chroma adapter and query contract.
   - `HybridQuery` and MCP tools already speak to the current vector seam.
   - Keeping Chroma avoids another adapter rewrite while the new embedded stack is still settling.

3. The marginal benefit of a LanceDB swap is now smaller.
   - Before the refactor, Chroma still implied a server in the Docker path.
   - After `SR-003`, the embedded path no longer requires a Chroma HTTP service.

4. The remaining high-value work is elsewhere.
   - Graph semantics and embedded operational stability matter more than changing the vector backend again.
   - The agent-facing value comes from the MetaOntology grammar and loop, not from a vector backend brand change.

## Why Not Now

Replacing Chroma with LanceDB would require at least:

- a new LanceDB adapter behind the vector seam
- ingest/query parity checks for metadata filters and result shaping
- MCP regression checks for `ontology_query` and `ontology_ingest`
- new operator guidance and support docs

That is real migration cost, but it no longer removes a major runtime dependency because the local Chroma path is already embedded.

## Triggers for Reconsideration

Re-open the LanceDB migration only if one of these becomes true:

1. Chroma local persistence becomes unstable or materially harder to operate.
2. OpenCrab needs tighter vector-table interoperability with the DuckDB-centric embedded stack.
3. Retrieval requirements expand beyond the current seam and justify a deeper vector rework.
4. A future benchmark shows a clear product-level gain, not just architectural neatness.

## Final Call

`Keep Chroma.`  
Treat LanceDB as an optional future optimization, not part of the current serverless migration.
