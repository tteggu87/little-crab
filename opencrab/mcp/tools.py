"""
MCP Tool Definitions for little-crab.

Each tool is a plain function that accepts keyword arguments and returns
a JSON-serialisable dict. The TOOLS registry maps tool names to their
schema (for tools/list) and their implementation function.

Tools:
  1. ontology_manifest          — full grammar as JSON
  2. ontology_add_node          — add/update a node
  3. ontology_add_edge          — add/update an edge (grammar-validated)
  4. ontology_query             — hybrid vector + graph search
  5. ontology_impact            — impact analysis (I1–I7)
  6. ontology_rebac_check       — ReBAC access check
  7. ontology_lever_simulate    — predict outcome changes from lever movement
  8. ontology_ingest            — ingest text into vector store
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Store / engine singletons (lazily initialised)
# ---------------------------------------------------------------------------
# These are populated by _get_context() which is called on first tool use.
# This design avoids importing heavy dependencies at module load time.

_context: dict[str, Any] = {}


def _get_context() -> dict[str, Any]:
    """Lazily initialise the local embedded stores and ontology engines."""
    global _context
    if _context:
        return _context

    from opencrab.config import get_settings
    from opencrab.ontology.builder import OntologyBuilder
    from opencrab.ontology.context_pipeline import AgentContextPipeline
    from opencrab.ontology.impact import ImpactEngine
    from opencrab.ontology.query import HybridQuery
    from opencrab.ontology.rebac import ReBACEngine
    from opencrab.stores.factory import make_doc_store, make_graph_store, make_sql_store, make_vector_store

    cfg = get_settings()

    graph = make_graph_store(cfg)
    vector = make_vector_store(cfg)
    docs = make_doc_store(cfg)
    sql = make_sql_store(cfg)

    builder = OntologyBuilder(graph, docs, sql)
    rebac = ReBACEngine(graph, sql)
    impact = ImpactEngine(graph, sql)
    hybrid = HybridQuery(vector, graph)
    context_pipeline = AgentContextPipeline(hybrid, docs, sql)

    _context = {
        "graph": graph,
        "vectors": vector,
        "documents": docs,
        "sql": sql,
        "builder": builder,
        "rebac": rebac,
        "impact": impact,
        "hybrid": hybrid,
        "context_pipeline": context_pipeline,
    }
    return _context


def reset_runtime_state() -> None:
    """Clear cached settings, stores, and tool context for in-process reloads."""
    global _context

    from opencrab.config import reset_settings_cache
    from opencrab.stores.factory import reset_store_caches

    _context = {}
    reset_settings_cache()
    reset_store_caches()


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------


def ontology_manifest() -> dict[str, Any]:
    """
    Return the full MetaOntology OS grammar.

    Includes spaces, meta-edges, impact categories, active metadata
    layers, and ReBAC configuration.
    """
    from opencrab.grammar.validator import describe_grammar

    return describe_grammar()


def ontology_add_node(
    space: str,
    node_type: str,
    node_id: str,
    properties: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Add or update a node in the MetaOntology graph.

    Parameters
    ----------
    space:
        MetaOntology space (e.g. "subject", "resource", "concept").
    node_type:
        Node type within that space (e.g. "User", "Document").
    node_id:
        Stable unique identifier.
    properties:
        Key/value properties for the node.
    """
    ctx = _get_context()
    try:
        return ctx["builder"].add_node(
            space=space,
            node_type=node_type,
            node_id=node_id,
            properties=properties or {},
        )
    except ValueError as exc:
        return {"error": str(exc), "valid": False}
    except Exception as exc:
        logger.error("ontology_add_node failed: %s", exc)
        return {"error": str(exc)}


def ontology_add_edge(
    from_space: str,
    from_id: str,
    relation: str,
    to_space: str,
    to_id: str,
    properties: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Add a directed edge between two ontology nodes.

    The (from_space, to_space, relation) triple is validated against
    the MetaOntology grammar before the write is attempted.

    Parameters
    ----------
    from_space:
        Space of the source node.
    from_id:
        ID of the source node.
    relation:
        Relation label (must be valid for the space pair).
    to_space:
        Space of the target node.
    to_id:
        ID of the target node.
    properties:
        Optional edge properties.
    """
    ctx = _get_context()
    try:
        return ctx["builder"].add_edge(
            from_space=from_space,
            from_id=from_id,
            relation=relation,
            to_space=to_space,
            to_id=to_id,
            properties=properties,
        )
    except ValueError as exc:
        return {"error": str(exc), "valid": False}
    except Exception as exc:
        logger.error("ontology_add_edge failed: %s", exc)
        return {"error": str(exc)}


def ontology_query(
    question: str,
    spaces: list[str] | None = None,
    limit: int = 10,
    project: str | None = None,
    source_id_prefix: str | None = None,
    subject_id: str | None = None,
    permission: str | None = None,
) -> dict[str, Any]:
    """
    Run a hybrid vector + graph query against the ontology.

    Parameters
    ----------
    question:
        Natural language question or keyword query.
    spaces:
        Optional list of space IDs to restrict the search.
    limit:
        Maximum number of results.
    project:
        Optional project metadata filter used to scope vector results.
    source_id_prefix:
        Optional source_id prefix used to scope vector results.
    subject_id:
        Optional subject ID used to add policy hints for relevant resource facts.
    permission:
        Optional permission label used with subject_id for policy hints.
    """
    ctx = _get_context()
    try:
        from opencrab.ontology.context_pipeline import AgentContextRequest

        bundle = ctx["context_pipeline"].build_context(
            AgentContextRequest(
                question=question,
                spaces=spaces,
                limit=limit,
                project=project,
                source_id_prefix=source_id_prefix,
                subject_id=subject_id,
                permission=permission,
            )
        )
        results = bundle.legacy_results()
        return {
            "question": question,
            "spaces_filter": spaces,
            "project_filter": project,
            "source_id_prefix_filter": source_id_prefix,
            "subject_id": subject_id,
            "permission": permission,
            "graph_expansion": bundle.scope["graph_expansion_enabled"],
            "total": len(results),
            "results": results,
            "context": bundle.to_dict(),
        }
    except Exception as exc:
        logger.error("ontology_query failed: %s", exc)
        return {"error": str(exc)}


def ontology_impact(
    node_id: str,
    change_type: str = "update",
) -> dict[str, Any]:
    """
    Analyse the impact of a change to a specific node.

    Returns which impact categories (I1–I7) are triggered,
    which neighbouring nodes are affected, and a human-readable summary.

    Parameters
    ----------
    node_id:
        ID of the node being changed.
    change_type:
        Nature of the change: create, update, delete, permission_change,
        relationship_add, relationship_remove, bulk_import.
    """
    ctx = _get_context()
    try:
        result = ctx["impact"].analyse(node_id=node_id, change_type=change_type)
        return result.to_dict()
    except Exception as exc:
        logger.error("ontology_impact failed: %s", exc)
        return {"error": str(exc)}


def ontology_rebac_check(
    subject_id: str,
    permission: str,
    resource_id: str,
) -> dict[str, Any]:
    """
    Check whether a subject has a given permission over a resource.

    Uses ReBAC (Relationship-Based Access Control): checks explicit SQL
    policies first, then traverses the graph for relationship-based access.

    Parameters
    ----------
    subject_id:
        ID of the subject (User, Team, Org, Agent).
    permission:
        One of: view, edit, execute, simulate, approve, admin.
    resource_id:
        ID of the resource being accessed.
    """
    ctx = _get_context()
    try:
        decision = ctx["rebac"].check(
            subject_id=subject_id,
            permission=permission,
            resource_id=resource_id,
        )
        return decision.to_dict()
    except Exception as exc:
        logger.error("ontology_rebac_check failed: %s", exc)
        return {"error": str(exc), "granted": False}


def ontology_lever_simulate(
    lever_id: str,
    direction: str,
    magnitude: float,
) -> dict[str, Any]:
    """
    Simulate the downstream effects of moving a lever.

    Predicts changes to connected Outcome nodes and affected Concepts
    based on the current graph structure.

    Parameters
    ----------
    lever_id:
        ID of the Lever node.
    direction:
        One of: raises, lowers, stabilizes, optimizes.
    magnitude:
        Strength of the lever movement (recommended 0.0–1.0).
    """
    ctx = _get_context()
    try:
        return ctx["impact"].lever_simulate(
            lever_id=lever_id,
            direction=direction,
            magnitude=float(magnitude),
        )
    except ValueError as exc:
        return {"error": str(exc)}
    except Exception as exc:
        logger.error("ontology_lever_simulate failed: %s", exc)
        return {"error": str(exc)}


def ontology_extract(
    text: str,
    source_id: str,
    model: str = "claude-haiku-4-5-20251001",
) -> dict[str, Any]:
    """
    Extract ontology nodes and edges from text and write them to the graph.

    little-crab currently uses a conservative local heuristic extractor that
    keeps the MCP surface available without requiring an external LLM service.

    Parameters
    ----------
    text:
        Raw text to extract knowledge from.
    source_id:
        Stable identifier for this source (e.g. file path or URL).
    model:
        Claude model to use for extraction.
    """
    from opencrab.ontology.extractor import LLMExtractor

    ctx = _get_context()

    try:
        extractor = LLMExtractor(model=model)
        result = extractor.extract_from_text(text, source_id=source_id)

        added_nodes = 0
        added_edges = 0
        node_errors: list[str] = []
        edge_errors: list[str] = []

        for node in result.nodes:
            try:
                ctx["builder"].add_node(
                    space=node.space,
                    node_type=node.node_type,
                    node_id=node.node_id,
                    properties=node.properties,
                )
                added_nodes += 1
            except Exception as exc:
                node_errors.append(f"{node.node_id}: {exc}")

        for edge in result.edges:
            try:
                ctx["builder"].add_edge(
                    from_space=edge.from_space,
                    from_id=edge.from_id,
                    relation=edge.relation,
                    to_space=edge.to_space,
                    to_id=edge.to_id,
                    properties=edge.properties,
                )
                added_edges += 1
            except Exception as exc:
                edge_errors.append(f"{edge.from_id}→{edge.to_id}: {exc}")

        return {
            "source_id": source_id,
            "extractor_mode": result.mode,
            "extracted_nodes": len(result.nodes),
            "extracted_edges": len(result.edges),
            "added_nodes": added_nodes,
            "added_edges": added_edges,
            "extraction_errors": result.errors,
            "node_errors": node_errors,
            "edge_errors": edge_errors,
        }
    except Exception as exc:
        logger.error("ontology_extract failed: %s", exc)
        return {"error": str(exc)}


def ontology_ingest(
    text: str,
    source_id: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Ingest a text document into the vector store.

    The text is embedded and stored in ChromaDB. A source record is
    also created in the embedded document store when available.

    Parameters
    ----------
    text:
        The text content to ingest.
    source_id:
        Stable unique identifier for this source document.
    metadata:
        Optional metadata (e.g. space, node_id, author, created_at).
    """
    ctx = _get_context()
    meta = metadata or {}
    result: dict[str, Any] = {"source_id": source_id, "stores": {}}

    # Ingest into vector store
    try:
        vector_result = ctx["hybrid"].ingest(text=text, source_id=source_id, metadata=meta)
        result["stores"].update(vector_result.get("stores", {}))
        if "vector_id" in vector_result:
            result["vector_id"] = vector_result["vector_id"]
    except Exception as exc:
        result["stores"]["vectors"] = f"error: {exc}"

    # Ingest into the document store
    documents: Any = ctx["documents"]
    if documents.available:
        try:
            document_id = documents.upsert_source(source_id, text, meta)
            result["stores"]["documents"] = f"ok (id={document_id})"
        except Exception as exc:
            result["stores"]["documents"] = f"error: {exc}"
    else:
        result["stores"]["documents"] = "unavailable"

    result["text_length"] = len(text)
    result["metadata"] = meta
    return result


# ---------------------------------------------------------------------------
# Tool registry (used by the MCP server for tools/list)
# ---------------------------------------------------------------------------

TOOL_SCHEMAS: dict[str, dict[str, Any]] = {
    "ontology_manifest": {
        "description": (
            "Return the full MetaOntology OS grammar: spaces, meta-edges, "
            "impact categories, active metadata layers, and ReBAC config."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    "ontology_add_node": {
        "description": "Add or update a node in the MetaOntology graph.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "space": {
                    "type": "string",
                    "description": "MetaOntology space (e.g. subject, resource, concept).",
                },
                "node_type": {
                    "type": "string",
                    "description": "Node type within the space (e.g. User, Document).",
                },
                "node_id": {
                    "type": "string",
                    "description": "Stable unique identifier for the node.",
                },
                "properties": {
                    "type": "object",
                    "description": "Optional key/value properties.",
                },
            },
            "required": ["space", "node_type", "node_id"],
        },
    },
    "ontology_add_edge": {
        "description": (
            "Add a directed edge between two nodes. Validates the relation "
            "against the MetaOntology grammar."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "from_space": {"type": "string", "description": "Source node space."},
                "from_id": {"type": "string", "description": "Source node ID."},
                "relation": {"type": "string", "description": "Relation label."},
                "to_space": {"type": "string", "description": "Target node space."},
                "to_id": {"type": "string", "description": "Target node ID."},
                "properties": {"type": "object", "description": "Optional edge properties."},
            },
            "required": ["from_space", "from_id", "relation", "to_space", "to_id"],
        },
    },
    "ontology_query": {
        "description": "Hybrid vector + graph search across the ontology.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "question": {"type": "string", "description": "Natural language query."},
                "spaces": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of spaces to filter results.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results (default 10).",
                    "default": 10,
                },
                "project": {
                    "type": "string",
                    "description": "Optional project metadata filter.",
                },
                "source_id_prefix": {
                    "type": "string",
                    "description": "Optional source_id prefix filter.",
                },
                "subject_id": {
                    "type": "string",
                    "description": "Optional subject ID used to add policy hints for relevant resources.",
                },
                "permission": {
                    "type": "string",
                    "description": "Optional permission used with subject_id for policy hints.",
                },
            },
            "required": ["question"],
        },
    },
    "ontology_impact": {
        "description": "Analyse the I1–I7 impact of a change to a node.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node_id": {"type": "string", "description": "ID of the node being changed."},
                "change_type": {
                    "type": "string",
                    "description": "Type of change: create, update, delete, etc.",
                    "default": "update",
                },
            },
            "required": ["node_id"],
        },
    },
    "ontology_rebac_check": {
        "description": "Check whether a subject has a permission over a resource.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "subject_id": {"type": "string", "description": "Subject node ID."},
                "permission": {
                    "type": "string",
                    "description": "Permission: view, edit, execute, simulate, approve, admin.",
                },
                "resource_id": {"type": "string", "description": "Resource node ID."},
            },
            "required": ["subject_id", "permission", "resource_id"],
        },
    },
    "ontology_lever_simulate": {
        "description": "Simulate downstream outcome changes from a lever movement.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "lever_id": {"type": "string", "description": "ID of the Lever node."},
                "direction": {
                    "type": "string",
                    "description": "Direction: raises, lowers, stabilizes, optimizes.",
                },
                "magnitude": {
                    "type": "number",
                    "description": "Strength of the lever movement (0.0–1.0).",
                },
            },
            "required": ["lever_id", "direction", "magnitude"],
        },
    },
    "ontology_extract": {
        "description": (
            "Extract ontology nodes and edges from text with the local heuristic "
            "extractor, then persist them into the knowledge graph."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to extract knowledge from."},
                "source_id": {"type": "string", "description": "Stable source identifier."},
                "model": {
                    "type": "string",
                    "description": "Claude model (default: claude-haiku-4-5-20251001).",
                    "default": "claude-haiku-4-5-20251001",
                },
            },
            "required": ["text", "source_id"],
        },
    },
    "ontology_ingest": {
        "description": "Ingest a text document into the vector and document stores.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text content to ingest."},
                "source_id": {"type": "string", "description": "Stable source identifier."},
                "metadata": {"type": "object", "description": "Optional metadata."},
            },
            "required": ["text", "source_id"],
        },
    },
}

# Callable map
_TOOL_FUNCTIONS: dict[str, Callable[..., Any]] = {
    "ontology_manifest": ontology_manifest,
    "ontology_add_node": ontology_add_node,
    "ontology_add_edge": ontology_add_edge,
    "ontology_query": ontology_query,
    "ontology_impact": ontology_impact,
    "ontology_rebac_check": ontology_rebac_check,
    "ontology_lever_simulate": ontology_lever_simulate,
    "ontology_extract": ontology_extract,
    "ontology_ingest": ontology_ingest,
}

# Combined tool descriptor list (name + schema)
TOOLS: list[dict[str, Any]] = [
    {"name": name, **schema}
    for name, schema in TOOL_SCHEMAS.items()
]


def dispatch_tool(name: str, arguments: dict[str, Any]) -> Any:
    """
    Look up and call a tool by name.

    Parameters
    ----------
    name:
        Tool name from TOOL_SCHEMAS.
    arguments:
        Arguments dict from the MCP tools/call request.

    Returns
    -------
    JSON-serialisable result.

    Raises
    ------
    KeyError
        If the tool name is not registered.
    """
    fn = _TOOL_FUNCTIONS.get(name)
    if fn is None:
        raise KeyError(f"Unknown tool: '{name}'. Available: {list(_TOOL_FUNCTIONS)}")
    return fn(**arguments)
