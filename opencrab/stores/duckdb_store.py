"""
DuckDB-backed embedded store for serverless OpenCrab mode.

This store keeps documents, events, registry state, policies, impacts, and
simulations in a single embedded database file while preserving the runtime
methods the builder, ingest flow, ReBAC engine, and impact engine already use.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class DuckDBStore:
    """Embedded document + registry + policy + analysis store."""

    def __init__(self, path: str) -> None:
        self._path = path
        self._duckdb: Any = None
        self._available = False
        self._lock = threading.RLock()
        self._connect()

    def _connect(self) -> None:
        try:
            import duckdb  # type: ignore[import]

            directory = os.path.dirname(self._path)
            if directory:
                os.makedirs(directory, exist_ok=True)
            self._duckdb = duckdb
            self._available = True
            self._create_tables()
            logger.info("DuckDB store connected (%s)", self._path)
        except Exception as exc:
            logger.warning("DuckDB store unavailable: %s", exc)
            self._available = False

    def _create_tables(self) -> None:
        ddl = [
            """
            CREATE TABLE IF NOT EXISTS node_documents (
                doc_id TEXT PRIMARY KEY,
                space TEXT NOT NULL,
                node_type TEXT NOT NULL,
                node_id TEXT NOT NULL,
                properties_json TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT current_timestamp,
                updated_at TIMESTAMP NOT NULL DEFAULT current_timestamp,
                UNIQUE(space, node_id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS source_documents (
                source_id TEXT PRIMARY KEY,
                text TEXT NOT NULL,
                metadata_json TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT current_timestamp,
                updated_at TIMESTAMP NOT NULL DEFAULT current_timestamp
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS audit_log (
                event_id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                actor TEXT NOT NULL,
                subject_id TEXT,
                details_json TEXT NOT NULL,
                timestamp TIMESTAMP NOT NULL DEFAULT current_timestamp
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS ontology_nodes (
                space TEXT NOT NULL,
                node_type TEXT NOT NULL,
                node_id TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT current_timestamp,
                updated_at TIMESTAMP NOT NULL DEFAULT current_timestamp,
                PRIMARY KEY(space, node_id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS ontology_edges (
                from_space TEXT NOT NULL,
                from_id TEXT NOT NULL,
                relation TEXT NOT NULL,
                to_space TEXT NOT NULL,
                to_id TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT current_timestamp,
                PRIMARY KEY(from_space, from_id, relation, to_space, to_id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS impact_records (
                id BIGINT PRIMARY KEY,
                node_id TEXT NOT NULL,
                change_type TEXT NOT NULL,
                impact_json TEXT NOT NULL,
                analyzed_at TIMESTAMP NOT NULL DEFAULT current_timestamp
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS lever_simulations (
                id BIGINT PRIMARY KEY,
                lever_id TEXT NOT NULL,
                direction TEXT NOT NULL,
                magnitude DOUBLE NOT NULL,
                results_json TEXT NOT NULL,
                simulated_at TIMESTAMP NOT NULL DEFAULT current_timestamp
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS rebac_policies (
                subject_id TEXT NOT NULL,
                permission TEXT NOT NULL,
                resource_id TEXT NOT NULL,
                granted BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP NOT NULL DEFAULT current_timestamp,
                PRIMARY KEY(subject_id, permission, resource_id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS staged_operations (
                stage_id TEXT PRIMARY KEY,
                entry_type TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'draft',
                created_at TIMESTAMP NOT NULL DEFAULT current_timestamp,
                published_at TIMESTAMP,
                publish_result_json TEXT NOT NULL DEFAULT '{}'
            )
            """,
        ]
        with self._connection() as conn:
            for statement in ddl:
                conn.execute(statement)

    @property
    def available(self) -> bool:
        return self._available

    def ping(self) -> bool:
        if not self._available:
            return False
        try:
            with self._connection() as conn:
                conn.execute("SELECT 1")
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _now(self) -> str:
        return datetime.now(UTC).isoformat()

    def _json_dump(self, payload: dict[str, Any]) -> str:
        return json.dumps(payload, ensure_ascii=False, default=str)

    def _json_load(self, payload: str | None) -> dict[str, Any]:
        if not payload:
            return {}
        return json.loads(payload)

    def _next_id(self, conn: Any, table: str) -> int:
        row = conn.execute(f"SELECT COALESCE(MAX(id), 0) + 1 FROM {table}").fetchone()  # noqa: S608
        return int(row[0]) if row else 1

    @contextmanager
    def _connection(self) -> Any:
        if self._duckdb is None:
            raise RuntimeError("DuckDB store is not available.")

        with self._lock:
            conn = self._duckdb.connect(self._path)
            try:
                yield conn
            finally:
                close = getattr(conn, "close", None)
                if callable(close):
                    close()

    # ------------------------------------------------------------------
    # Node document operations
    # ------------------------------------------------------------------

    def upsert_node_doc(
        self,
        space: str,
        node_type: str,
        node_id: str,
        properties: dict[str, Any],
    ) -> str:
        if not self._available:
            raise RuntimeError("DuckDB store is not available.")

        doc_id = f"{space}::{node_id}"
        now = self._now()
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO node_documents
                    (doc_id, space, node_type, node_id, properties_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (doc_id) DO UPDATE SET
                    node_type = EXCLUDED.node_type,
                    properties_json = EXCLUDED.properties_json,
                    updated_at = EXCLUDED.updated_at
                """,
                [doc_id, space, node_type, node_id, self._json_dump(properties), now, now],
            )
        return doc_id

    def get_node_doc(self, space: str, node_id: str) -> dict[str, Any] | None:
        if not self._available:
            raise RuntimeError("DuckDB store is not available.")

        with self._connection() as conn:
            row = conn.execute(
                """
                SELECT space, node_type, node_id, properties_json, created_at, updated_at
                FROM node_documents
                WHERE space = ? AND node_id = ?
                """,
                [space, node_id],
            ).fetchone()
        if row is None:
            return None
        return {
            "space": row[0],
            "node_type": row[1],
            "node_id": row[2],
            "properties": self._json_load(row[3]),
            "created_at": str(row[4]),
            "updated_at": str(row[5]),
        }

    def get_node_docs(
        self, node_refs: list[tuple[str, str]]
    ) -> dict[tuple[str, str], dict[str, Any]]:
        if not self._available:
            raise RuntimeError("DuckDB store is not available.")
        if not node_refs:
            return {}

        refs = list(dict.fromkeys(node_refs))
        placeholders = ", ".join(["(?, ?)"] * len(refs))
        params = [value for ref in refs for value in ref]

        with self._connection() as conn:
            rows = conn.execute(
                f"""
                SELECT d.space, d.node_type, d.node_id, d.properties_json, d.created_at, d.updated_at
                FROM node_documents AS d
                INNER JOIN (VALUES {placeholders}) AS refs(space, node_id)
                    ON d.space = refs.space AND d.node_id = refs.node_id
                """,
                params,
            ).fetchall()

        return {
            (str(row[0]), str(row[2])): {
                "space": row[0],
                "node_type": row[1],
                "node_id": row[2],
                "properties": self._json_load(row[3]),
                "created_at": str(row[4]),
                "updated_at": str(row[5]),
            }
            for row in rows
        }

    def list_nodes(self, space: str | None = None) -> list[dict[str, Any]]:
        if not self._available:
            raise RuntimeError("DuckDB store is not available.")

        query = """
            SELECT space, node_type, node_id, properties_json, created_at, updated_at
            FROM node_documents
        """
        params: list[Any] = []
        if space:
            query += " WHERE space = ?"
            params.append(space)
        query += " ORDER BY updated_at DESC"
        with self._connection() as conn:
            rows = conn.execute(query, params).fetchall()
        return [
            {
                "space": row[0],
                "node_type": row[1],
                "node_id": row[2],
                "properties": self._json_load(row[3]),
                "created_at": str(row[4]),
                "updated_at": str(row[5]),
            }
            for row in rows
        ]

    def delete_node_doc(self, space: str, node_id: str) -> bool:
        if not self._available:
            raise RuntimeError("DuckDB store is not available.")

        with self._connection() as conn:
            row = conn.execute(
                "DELETE FROM node_documents WHERE space = ? AND node_id = ? RETURNING node_id",
                [space, node_id],
            ).fetchone()
        return row is not None

    # ------------------------------------------------------------------
    # Source / ingestion records
    # ------------------------------------------------------------------

    def upsert_source(
        self,
        source_id: str,
        text: str,
        metadata: dict[str, Any],
    ) -> str:
        if not self._available:
            raise RuntimeError("DuckDB store is not available.")

        now = self._now()
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO source_documents
                    (source_id, text, metadata_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT (source_id) DO UPDATE SET
                    text = EXCLUDED.text,
                    metadata_json = EXCLUDED.metadata_json,
                    updated_at = EXCLUDED.updated_at
                """,
                [source_id, text, self._json_dump(metadata), now, now],
            )
        return source_id

    def upsert_sources(self, records: list[dict[str, Any]]) -> list[str]:
        if not self._available:
            raise RuntimeError("DuckDB store is not available.")
        if not records:
            return []

        now = self._now()
        rows = [
            [
                str(record["source_id"]),
                str(record["text"]),
                self._json_dump(dict(record.get("metadata") or {})),
                now,
                now,
            ]
            for record in records
        ]

        with self._connection() as conn:
            conn.executemany(
                """
                INSERT INTO source_documents
                    (source_id, text, metadata_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT (source_id) DO UPDATE SET
                    text = EXCLUDED.text,
                    metadata_json = EXCLUDED.metadata_json,
                    updated_at = EXCLUDED.updated_at
                """,
                rows,
            )
        return [str(record["source_id"]) for record in records]

    def get_source(self, source_id: str) -> dict[str, Any] | None:
        if not self._available:
            raise RuntimeError("DuckDB store is not available.")

        with self._connection() as conn:
            row = conn.execute(
                """
                SELECT source_id, text, metadata_json, created_at, updated_at
                FROM source_documents
                WHERE source_id = ?
                """,
                [source_id],
            ).fetchone()
        if row is None:
            return None
        return {
            "source_id": row[0],
            "text": row[1],
            "metadata": self._json_load(row[2]),
            "created_at": str(row[3]),
            "updated_at": str(row[4]),
        }

    def get_sources(self, source_ids: list[str]) -> dict[str, dict[str, Any]]:
        if not self._available:
            raise RuntimeError("DuckDB store is not available.")
        if not source_ids:
            return {}

        ids = list(dict.fromkeys(source_ids))
        placeholders = ", ".join(["?"] * len(ids))

        with self._connection() as conn:
            rows = conn.execute(
                f"""
                SELECT source_id, text, metadata_json, created_at, updated_at
                FROM source_documents
                WHERE source_id IN ({placeholders})
                """,
                ids,
            ).fetchall()

        return {
            str(row[0]): {
                "source_id": row[0],
                "text": row[1],
                "metadata": self._json_load(row[2]),
                "created_at": str(row[3]),
                "updated_at": str(row[4]),
            }
            for row in rows
        }

    def list_sources(self, limit: int = 100) -> list[dict[str, Any]]:
        if not self._available:
            raise RuntimeError("DuckDB store is not available.")

        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT source_id, metadata_json, created_at, updated_at
                FROM source_documents
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                [limit],
            ).fetchall()
        return [
            {
                "source_id": row[0],
                "metadata": self._json_load(row[1]),
                "created_at": str(row[2]),
                "updated_at": str(row[3]),
            }
            for row in rows
        ]

    # ------------------------------------------------------------------
    # Audit log
    # ------------------------------------------------------------------

    def log_event(
        self,
        event_type: str,
        subject_id: str | dict[str, Any] | None = None,
        details: dict[str, Any] | None = None,
        actor: str = "system",
    ) -> None:
        if not self._available:
            return

        if isinstance(subject_id, dict) and details is None:
            details = subject_id
            subject_id = None

        timestamp = self._now()
        event_id = f"{event_type}::{timestamp}"
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO audit_log
                    (event_id, event_type, actor, subject_id, details_json, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    event_id,
                    event_type,
                    actor,
                    subject_id,
                    self._json_dump(details or {}),
                    timestamp,
                ],
            )

    def get_audit_log(
        self, limit: int = 100, event_type: str | None = None
    ) -> list[dict[str, Any]]:
        if not self._available:
            raise RuntimeError("DuckDB store is not available.")

        query = """
            SELECT event_type, actor, subject_id, details_json, timestamp
            FROM audit_log
        """
        params: list[Any] = []
        if event_type:
            query += " WHERE event_type = ?"
            params.append(event_type)
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        with self._connection() as conn:
            rows = conn.execute(query, params).fetchall()
        return [
            {
                "event_type": row[0],
                "actor": row[1],
                "subject_id": row[2],
                "details": self._json_load(row[3]),
                "timestamp": str(row[4]),
            }
            for row in rows
        ]

    # ------------------------------------------------------------------
    # Registry
    # ------------------------------------------------------------------

    def register_node(self, space: str, node_type: str, node_id: str) -> None:
        if not self._available:
            raise RuntimeError("DuckDB store is not available.")

        now = self._now()
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO ontology_nodes
                    (space, node_type, node_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT (space, node_id) DO UPDATE SET
                    node_type = EXCLUDED.node_type,
                    updated_at = EXCLUDED.updated_at
                """,
                [space, node_type, node_id, now, now],
            )

    def register_edge(
        self, from_space: str, from_id: str, relation: str, to_space: str, to_id: str
    ) -> None:
        if not self._available:
            raise RuntimeError("DuckDB store is not available.")

        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO ontology_edges
                    (from_space, from_id, relation, to_space, to_id)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT (from_space, from_id, relation, to_space, to_id) DO NOTHING
                """,
                [from_space, from_id, relation, to_space, to_id],
            )

    def list_edges(self, limit: int = 1000) -> list[dict[str, Any]]:
        if not self._available:
            raise RuntimeError("DuckDB store is not available.")

        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT from_space, from_id, relation, to_space, to_id, created_at
                FROM ontology_edges
                ORDER BY created_at ASC
                LIMIT ?
                """,
                [limit],
            ).fetchall()
        return [
            {
                "from_space": row[0],
                "from_id": row[1],
                "relation": row[2],
                "to_space": row[3],
                "to_id": row[4],
                "created_at": str(row[5]),
            }
            for row in rows
        ]

    # ------------------------------------------------------------------
    # Impact records
    # ------------------------------------------------------------------

    def save_impact(self, node_id: str, change_type: str, impact: dict[str, Any]) -> int:
        if not self._available:
            raise RuntimeError("DuckDB store is not available.")

        now = self._now()
        with self._connection() as conn:
            row_id = self._next_id(conn, "impact_records")
            conn.execute(
                """
                INSERT INTO impact_records (id, node_id, change_type, impact_json, analyzed_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                [row_id, node_id, change_type, self._json_dump(impact), now],
            )
        return row_id

    def get_impacts(self, node_id: str, limit: int = 20) -> list[dict[str, Any]]:
        if not self._available:
            raise RuntimeError("DuckDB store is not available.")

        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT id, node_id, change_type, impact_json, analyzed_at
                FROM impact_records
                WHERE node_id = ?
                ORDER BY analyzed_at DESC
                LIMIT ?
                """,
                [node_id, limit],
            ).fetchall()
        return [
            {
                "id": row[0],
                "node_id": row[1],
                "change_type": row[2],
                "impact": self._json_load(row[3]),
                "analyzed_at": str(row[4]),
            }
            for row in rows
        ]

    # ------------------------------------------------------------------
    # Lever simulations
    # ------------------------------------------------------------------

    def save_simulation(
        self, lever_id: str, direction: str, magnitude: float, results: dict[str, Any]
    ) -> int:
        if not self._available:
            raise RuntimeError("DuckDB store is not available.")

        now = self._now()
        with self._connection() as conn:
            row_id = self._next_id(conn, "lever_simulations")
            conn.execute(
                """
                INSERT INTO lever_simulations
                    (id, lever_id, direction, magnitude, results_json, simulated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [row_id, lever_id, direction, magnitude, self._json_dump(results), now],
            )
        return row_id

    # ------------------------------------------------------------------
    # ReBAC policies
    # ------------------------------------------------------------------

    def set_policy(
        self,
        subject_id: str,
        permission: str,
        resource_id: str,
        granted: bool = True,
    ) -> None:
        if not self._available:
            raise RuntimeError("DuckDB store is not available.")

        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO rebac_policies
                    (subject_id, permission, resource_id, granted)
                VALUES (?, ?, ?, ?)
                ON CONFLICT (subject_id, permission, resource_id) DO UPDATE SET
                    granted = EXCLUDED.granted
                """,
                [subject_id, permission, resource_id, granted],
            )

    def check_policy(self, subject_id: str, permission: str, resource_id: str) -> bool | None:
        if not self._available:
            raise RuntimeError("DuckDB store is not available.")

        with self._connection() as conn:
            row = conn.execute(
                """
                SELECT granted
                FROM rebac_policies
                WHERE subject_id = ? AND permission = ? AND resource_id = ?
                """,
                [subject_id, permission, resource_id],
            ).fetchone()
        if row is None:
            return None
        return bool(row[0])

    def check_policies(
        self,
        subject_id: str,
        permission: str,
        resource_ids: list[str],
    ) -> dict[str, bool]:
        if not self._available:
            raise RuntimeError("DuckDB store is not available.")
        if not resource_ids:
            return {}

        ids = list(dict.fromkeys(resource_ids))
        placeholders = ", ".join(["?"] * len(ids))
        params = [subject_id, permission, *ids]

        with self._connection() as conn:
            rows = conn.execute(
                f"""
                SELECT resource_id, granted
                FROM rebac_policies
                WHERE subject_id = ? AND permission = ? AND resource_id IN ({placeholders})
                """,
                params,
            ).fetchall()

        return {str(row[0]): bool(row[1]) for row in rows}

    def list_policies(self, subject_id: str) -> list[dict[str, Any]]:
        if not self._available:
            raise RuntimeError("DuckDB store is not available.")

        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT subject_id, permission, resource_id, granted, created_at
                FROM rebac_policies
                WHERE subject_id = ?
                ORDER BY created_at ASC
                """,
                [subject_id],
            ).fetchall()
        return [
            {
                "subject_id": row[0],
                "permission": row[1],
                "resource_id": row[2],
                "granted": bool(row[3]),
                "created_at": str(row[4]),
            }
            for row in rows
        ]

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def stage_node(
        self,
        space: str,
        node_type: str,
        node_id: str,
        properties: dict[str, Any],
    ) -> str:
        if not self._available:
            raise RuntimeError("DuckDB store is not available.")

        stage_id = f"stage-{uuid4().hex[:12]}"
        payload = {
            "space": space,
            "node_type": node_type,
            "node_id": node_id,
            "properties": properties,
        }
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO staged_operations
                    (stage_id, entry_type, payload_json, status, publish_result_json)
                VALUES (?, 'node', ?, 'draft', '{}')
                """,
                [stage_id, self._json_dump(payload)],
            )
        return stage_id

    def stage_edge(
        self,
        from_space: str,
        from_id: str,
        relation: str,
        to_space: str,
        to_id: str,
        properties: dict[str, Any] | None = None,
    ) -> str:
        if not self._available:
            raise RuntimeError("DuckDB store is not available.")

        stage_id = f"stage-{uuid4().hex[:12]}"
        payload = {
            "from_space": from_space,
            "from_id": from_id,
            "relation": relation,
            "to_space": to_space,
            "to_id": to_id,
            "properties": properties or {},
        }
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO staged_operations
                    (stage_id, entry_type, payload_json, status, publish_result_json)
                VALUES (?, 'edge', ?, 'draft', '{}')
                """,
                [stage_id, self._json_dump(payload)],
            )
        return stage_id

    def get_staged_operation(self, stage_id: str) -> dict[str, Any] | None:
        if not self._available:
            raise RuntimeError("DuckDB store is not available.")

        with self._connection() as conn:
            row = conn.execute(
                """
                SELECT stage_id, entry_type, payload_json, status,
                       created_at, published_at, publish_result_json
                FROM staged_operations
                WHERE stage_id = ?
                """,
                [stage_id],
            ).fetchone()
        if row is None:
            return None
        return {
            "stage_id": row[0],
            "entry_type": row[1],
            "payload": self._json_load(row[2]),
            "status": row[3],
            "created_at": str(row[4]),
            "published_at": str(row[5]) if row[5] is not None else None,
            "publish_result": self._json_load(row[6]),
        }

    def list_staged_operations(
        self,
        status: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        if not self._available:
            raise RuntimeError("DuckDB store is not available.")

        query = """
            SELECT stage_id, entry_type, payload_json, status,
                   created_at, published_at, publish_result_json
            FROM staged_operations
        """
        params: list[Any] = []
        if status:
            query += " WHERE status = ?"
            params.append(status)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        with self._connection() as conn:
            rows = conn.execute(query, params).fetchall()
        return [
            {
                "stage_id": row[0],
                "entry_type": row[1],
                "payload": self._json_load(row[2]),
                "status": row[3],
                "created_at": str(row[4]),
                "published_at": str(row[5]) if row[5] is not None else None,
                "publish_result": self._json_load(row[6]),
            }
            for row in rows
        ]

    def mark_staged_published(
        self,
        stage_id: str,
        publish_result: dict[str, Any] | None = None,
    ) -> None:
        if not self._available:
            raise RuntimeError("DuckDB store is not available.")

        now = self._now()
        with self._connection() as conn:
            conn.execute(
                """
                UPDATE staged_operations
                SET status = 'published',
                    published_at = ?,
                    publish_result_json = ?
                WHERE stage_id = ?
                """,
                [now, self._json_dump(publish_result or {}), stage_id],
            )

    def mark_staged_failed(
        self,
        stage_id: str,
        publish_result: dict[str, Any] | None = None,
    ) -> None:
        if not self._available:
            raise RuntimeError("DuckDB store is not available.")

        with self._connection() as conn:
            conn.execute(
                """
                UPDATE staged_operations
                SET status = 'failed',
                    publish_result_json = ?
                WHERE stage_id = ?
                """,
                [self._json_dump(publish_result or {}), stage_id],
            )

    def collection_stats(self) -> dict[str, int]:
        if not self._available:
            return {}
        return {
            "nodes": self._count("node_documents"),
            "sources": self._count("source_documents"),
            "audit_log": self._count("audit_log"),
        }

    def table_counts(self) -> dict[str, int]:
        if not self._available:
            return {}

        tables = [
            "node_documents",
            "source_documents",
            "audit_log",
            "ontology_nodes",
            "ontology_edges",
            "impact_records",
            "lever_simulations",
            "rebac_policies",
            "staged_operations",
        ]
        return {table: self._count(table) for table in tables}

    def stats(self) -> dict[str, Any]:
        return {
            "path": self._path,
            **self.collection_stats(),
        }

    def _count(self, table: str) -> int:
        with self._connection() as conn:
            row = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()  # noqa: S608
        return int(row[0]) if row else 0
