---
status: Active
source_of_truth: Yes
last_updated: 2026-03-26
superseded_by: N/A
---

# Architecture

## Top-Level Shape

little-crab is a local-only ontology runtime with two user-facing surfaces:

1. CLI
2. MCP stdio server

Both surfaces call the same Python runtime and share the same embedded stores.

This fork intentionally preserves OpenCrab's core architectural meaning: grammar-first writes, agent-facing tools, and a runtime that tolerates incomplete knowledge while allowing later graph growth.

## Data Flow

- CLI or MCP request enters the runtime.
- Grammar and validator gate writes and relation legality.
- Ontology runtime coordinates graph, operational, and vector operations.
- Results return to the CLI or MCP caller.

## Component Roles

### Grammar Layer

- Defines the 9 spaces and valid relations.
- Rejects invalid node and edge writes before persistence.
- Gives agents a bounded ontology coordinate system so they can classify partial knowledge before the full model exists.

### Runtime Layer

- `OntologyBuilder` coordinates node/edge writes.
- `HybridQuery` combines vector hits and graph expansion.
- `ReBACEngine` resolves explicit policy plus graph access paths.
- `ImpactEngine` computes impact categories and persists analysis records.
- `LLMExtractor` currently runs a deterministic heuristic extraction pass.
- Together these components preserve OpenCrab's agentic loop: classify, connect, retrieve, inspect, and later fill missing structure.

### Storage Layer

- `LadybugStore` owns graph traversal and path expansion.
- `DuckDBStore` owns:
  - node documents
  - source documents
  - audit log
  - node registry
  - edge registry
  - ReBAC policies
  - impact records
  - lever simulations
- `ChromaStore` owns text embeddings and similarity retrieval.

## Invariants

- The OpenCrab grammar and MCP tool names are preserved.
- The OpenCrab strength being preserved is not the old service stack; it is the ontology discipline plus the agent-facing growth loop.
- `node_id` remains globally unique across spaces.
- The runtime is local-only.
- The package surface is `little-crab`, while the import namespace remains `opencrab`.

## Intentional Compatibility

- The `opencrab` CLI alias is still live.
- The old service-backed stores are removed.
- Dated docs remain as design notes, not canonical runtime docs.
