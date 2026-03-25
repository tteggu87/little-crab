"""
Store factory — returns the right backend based on STORAGE_MODE setting.

Usage:
    from opencrab.stores.factory import make_graph_store, make_vector_store, ...
    graph  = make_graph_store(settings)
    vector = make_vector_store(settings)
    docs   = make_doc_store(settings)
    sql    = make_sql_store(settings)
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from opencrab.config import Settings


_LOCAL_DUCKDB_STORES: dict[str, Any] = {}


def _make_local_duckdb_store(settings: Settings) -> Any:
    from opencrab.stores.duckdb_store import DuckDBStore

    db_path = os.path.join(settings.local_data_dir, "opencrab.db")
    store = _LOCAL_DUCKDB_STORES.get(db_path)
    if store is None:
        store = DuckDBStore(path=db_path)
        _LOCAL_DUCKDB_STORES[db_path] = store
    return store


def make_graph_store(settings: Settings) -> Any:
    """Return LadybugStore (local) or Neo4jStore (docker)."""
    if settings.is_local:
        from opencrab.stores.ladybug_store import LadybugStore

        db_path = os.path.join(settings.local_data_dir, "graph.lbug")
        return LadybugStore(db_path=db_path)
    else:
        from opencrab.stores.neo4j_store import Neo4jStore

        return Neo4jStore(
            uri=settings.neo4j_uri,
            user=settings.neo4j_user,
            password=settings.neo4j_password,
        )


def make_vector_store(settings: Settings) -> Any:
    """Return ChromaStore in local or docker mode."""
    from opencrab.stores.chroma_store import ChromaStore

    chroma_path = os.path.join(settings.local_data_dir, "chroma")
    return ChromaStore(
        host=settings.chroma_host,
        port=settings.chroma_port,
        collection_name=settings.chroma_collection,
        local_mode=settings.is_local,
        local_path=chroma_path,
    )


def make_doc_store(settings: Settings) -> Any:
    """Return DuckDBStore (local) or MongoStore (docker)."""
    if settings.is_local:
        return _make_local_duckdb_store(settings)
    else:
        from opencrab.stores.mongo_store import MongoStore

        return MongoStore(uri=settings.mongodb_uri, db_name=settings.mongodb_db)


def make_sql_store(settings: Settings) -> Any:
    """Return DuckDBStore (local) or SQLStore (docker)."""
    if settings.is_local:
        return _make_local_duckdb_store(settings)

    from opencrab.stores.sql_store import SQLStore

    return SQLStore(url=settings.postgres_url)
