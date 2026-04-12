"""Local-only store factory for little-crab."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from opencrab.config import Settings


_LOCAL_DUCKDB_STORES: dict[str, Any] = {}
_LOCAL_LADYBUG_STORES: dict[str, Any] = {}
_LOCAL_CHROMA_STORES: dict[tuple[str, str, str, str, str, int], Any] = {}


@dataclass(frozen=True)
class RuntimeStores:
    graph: Any
    vector: Any
    documents: Any
    sql: Any


@dataclass(frozen=True)
class RuntimeServices:
    stores: RuntimeStores
    builder: Any
    rebac: Any
    impact: Any
    hybrid: Any
    context_pipeline: Any


def _make_local_duckdb_store(settings: Settings) -> Any:
    from opencrab.stores.duckdb_store import DuckDBStore

    db_path = os.path.join(settings.local_data_dir, "opencrab.db")
    store = _LOCAL_DUCKDB_STORES.get(db_path)
    if store is None:
        store = DuckDBStore(path=db_path)
        if store.available:
            _LOCAL_DUCKDB_STORES[db_path] = store
    return store


def _make_local_ladybug_store(settings: Settings) -> Any:
    from opencrab.stores.ladybug_store import LadybugStore

    db_path = os.path.join(settings.local_data_dir, "graph.lbug")
    store = _LOCAL_LADYBUG_STORES.get(db_path)
    if store is None:
        store = LadybugStore(db_path=db_path)
        if store.available:
            _LOCAL_LADYBUG_STORES[db_path] = store
    return store


def make_graph_store(settings: Settings) -> Any:
    """Return the shared embedded Ladybug graph store."""
    return _make_local_ladybug_store(settings)


def make_vector_store(settings: Settings) -> Any:
    """Return the shared embedded Chroma vector store."""
    from opencrab.stores.chroma_store import ChromaStore

    chroma_path = os.path.join(settings.local_data_dir, "chroma")
    chroma_options = settings.chroma_runtime_options
    cache_key = (
        chroma_path,
        str(chroma_options["collection_name"]),
        str(chroma_options["embedding_provider"]),
        str(chroma_options["ollama_url"]),
        str(chroma_options["ollama_embedding_model"]),
        int(chroma_options["ollama_timeout"]),
    )
    store = _LOCAL_CHROMA_STORES.get(cache_key)
    if store is None:
        store = ChromaStore(
            host="localhost",
            port=8000,
            collection_name=str(chroma_options["collection_name"]),
            local_mode=True,
            local_path=chroma_path,
            embedding_provider=str(chroma_options["embedding_provider"]),
            ollama_url=str(chroma_options["ollama_url"]),
            ollama_embedding_model=str(chroma_options["ollama_embedding_model"]),
            ollama_timeout=int(chroma_options["ollama_timeout"]),
        )
        if store.available:
            _LOCAL_CHROMA_STORES[cache_key] = store
    return store


def make_doc_store(settings: Settings) -> Any:
    """Return the shared embedded DuckDB document/event store."""
    return _make_local_duckdb_store(settings)


def make_sql_store(settings: Settings) -> Any:
    """Return the shared embedded DuckDB registry/policy/analysis store."""
    return _make_local_duckdb_store(settings)


def make_runtime_stores(settings: Settings) -> RuntimeStores:
    """Return the shared store bundle for the active local runtime."""
    return RuntimeStores(
        graph=make_graph_store(settings),
        vector=make_vector_store(settings),
        documents=make_doc_store(settings),
        sql=make_sql_store(settings),
    )


def make_runtime_services(settings: Settings) -> RuntimeServices:
    """Return the assembled ontology runtime services for the active local profile."""
    from opencrab.ontology.builder import OntologyBuilder
    from opencrab.ontology.context_pipeline import AgentContextPipeline
    from opencrab.ontology.impact import ImpactEngine
    from opencrab.ontology.query import HybridQuery
    from opencrab.ontology.rebac import ReBACEngine

    stores = make_runtime_stores(settings)
    hybrid = HybridQuery(stores.vector, stores.graph)
    return RuntimeServices(
        stores=stores,
        builder=OntologyBuilder(stores.graph, stores.documents, stores.sql),
        rebac=ReBACEngine(stores.graph, stores.sql),
        impact=ImpactEngine(stores.graph, stores.sql),
        hybrid=hybrid,
        context_pipeline=AgentContextPipeline(hybrid, stores.documents, stores.sql),
    )


def reset_store_caches() -> None:
    """Clear cached embedded store instances for tests and host reloads."""
    _LOCAL_DUCKDB_STORES.clear()
    _LOCAL_LADYBUG_STORES.clear()
    _LOCAL_CHROMA_STORES.clear()
