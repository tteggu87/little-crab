"""Local-only store factory for little-crab."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from opencrab.config import Settings


_LOCAL_DUCKDB_STORES: dict[str, Any] = {}
_LOCAL_LADYBUG_STORES: dict[str, Any] = {}


def _make_local_duckdb_store(settings: Settings) -> Any:
    from opencrab.stores.duckdb_store import DuckDBStore

    db_path = os.path.join(settings.local_data_dir, "opencrab.db")
    store = _LOCAL_DUCKDB_STORES.get(db_path)
    if store is None:
        store = DuckDBStore(path=db_path)
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
    return ChromaStore(
        host="localhost",
        port=8000,
        collection_name=settings.chroma_collection,
        local_mode=True,
        local_path=chroma_path,
    )


def make_doc_store(settings: Settings) -> Any:
    """Return the shared embedded DuckDB document/event store."""
    return _make_local_duckdb_store(settings)


def make_sql_store(settings: Settings) -> Any:
    """Return the shared embedded DuckDB registry/policy/analysis store."""
    return _make_local_duckdb_store(settings)
