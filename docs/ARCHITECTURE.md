---
status: Active
source_of_truth: Yes
last_updated: 2026-03-27
superseded_by: N/A
---

# Architecture

## Top-Level Shape

little-crab is a local-only ontology runtime with two user-facing surfaces:

1. CLI
2. MCP stdio server

Both surfaces call the same Python runtime and share the same embedded stores.

This fork intentionally preserves OpenCrab's core architectural meaning: grammar-first writes, agent-facing tools, and a runtime that tolerates incomplete knowledge while allowing later graph growth.

The MCP stdio surface is intentionally lightweight but now covers the client lifecycle steps that modern MCP hosts expect during startup: protocol version negotiation, `notifications/initialized`, tool discovery, empty resource discovery, and batched JSON-RPC follow-up messages.

The same preservation goal also applies to future read models and visualization layers: they should keep incomplete knowledge visible, support non-English query paths, and preserve enough provenance depth to explain multi-step reasoning instead of collapsing it into a shallow summary.

## Data Flow

- CLI or MCP request enters the runtime.
- Grammar and validator gate writes and relation legality.
- Ontology runtime coordinates graph, operational, and vector operations.
- Agent-facing read paths can assemble a derived context bundle through the agent context pipeline without changing canonical store ownership.
- Results return to the CLI or MCP caller.

## Component Roles

### Grammar Layer

- Defines the 9 spaces and valid relations.
- Rejects invalid node and edge writes before persistence.
- Gives agents a bounded ontology coordinate system so they can classify partial knowledge before the full model exists.

### Runtime Layer

- `OntologyBuilder` coordinates node/edge writes.
- `AgentContextPipeline` assembles one read-only bundle for agent-facing reasoning from the live local stores.
- `HybridQuery` combines vector hits and graph expansion.
- `ReBACEngine` resolves explicit policy plus graph access paths.
- `ImpactEngine` computes impact categories and persists analysis records.
- `LLMExtractor` currently runs a deterministic heuristic extraction pass.
- Together these components preserve OpenCrab's agentic loop: classify, connect, retrieve, inspect, and later fill missing structure.

### Storage Layer

- `LadybugStore` owns graph traversal and path expansion.
- `LadybugStore` is the canonical store for ontology entity and relation truth.
- `DuckDBStore` owns:
  - node documents
  - source documents
  - audit log
  - node registry
  - edge registry
  - ReBAC policies
  - impact records
  - lever simulations
- `DuckDBStore` is the canonical store for documentary, provenance, registry, policy, audit, and impact truth.
- `ChromaStore` owns text embeddings and similarity retrieval.
- `ChromaStore` is a derived retrieval index only and must not be treated as canonical truth.

## Invariants

- The OpenCrab grammar and MCP tool names are preserved.
- The MCP stdio server must remain compatible with modern host startup expectations for negotiated protocol versions, initialized notifications, empty resource discovery, and batched follow-up requests.
- The OpenCrab strength being preserved is not the old service stack; it is the ontology discipline plus the agent-facing growth loop.
- OpenCrab flexibility is part of the preserved meaning: partial knowledge must remain usable, non-English query paths should remain viable, and provenance should stay deep enough to explain multi-step links.
- Live node and edge truth come from graph persistence first. Registry rows and successful structural audit events must not be emitted when the graph record itself was not written.
- Scoped query filters such as `project` and `source_id_prefix` intentionally disable graph expansion so hybrid results do not escape the caller's requested scope.
- Embedded runtime state can be reset explicitly for tests and host reloads so settings and store caches rebuild against the current local configuration.
- Agent-context enrichment is best-effort; supporting evidence and policy hint lookup failures should degrade into uncertainty and gap markers instead of aborting the full read path.
- Agent-facing context is derived, read-only output from `AgentContextPipeline`; it must not become a second canonical persistence layer.
- `node_id` remains globally unique across spaces.
- The runtime is local-only.
- The package surface is `little-crab`, while the import namespace remains `opencrab`.
- The canonical CLI command is `littlecrab`, with `ltcrab` as a supported short alias.

## Intentional Compatibility

- The `opencrab` CLI alias is still live as deprecated compatibility.
- The old service-backed stores are removed.
- Dated docs remain as design notes, not canonical runtime docs.
