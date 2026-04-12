"""
LadybugDB-backed graph store for embedded OpenCrab mode.

The store keeps OpenCrab's graph contract intact while using a single
`OntologyNode` node table and one relationship table per MetaOntology relation.
The runtime only relies on a small Cypher subset, so `run_cypher()` focuses on
the query shapes used by builder/query/rebac/impact instead of full Cypher
compatibility.
"""

from __future__ import annotations

import ast
import base64
import json
import logging
import os
import re
import threading
import time
from collections import deque
from contextlib import contextmanager
from typing import Any, cast

from opencrab.grammar.manifest import all_relations

logger = logging.getLogger(__name__)

_SAFE_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class LadybugStore:
    """LadybugDB-backed graph store."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._lb: Any = None
        self._available = False
        self._op_lock = threading.RLock()
        self._connect()

    def _connect(self) -> None:
        try:
            import real_ladybug as lb  # type: ignore[import]

            directory = os.path.dirname(self._db_path)
            if directory:
                os.makedirs(directory, exist_ok=True)

            self._lb = lb
            self._available = True
            self._ensure_schema()
            logger.info("LadybugStore initialised at %s", self._db_path)
        except Exception as exc:
            logger.warning("LadybugStore init failed: %s", exc)
            self._available = False

    @property
    def available(self) -> bool:
        return self._available

    def close(self) -> None:
        # Connections are opened per operation, so there is no persistent
        # handle to close here.
        return None

    def ping(self) -> bool:
        try:
            self._execute("MATCH (n:OntologyNode) RETURN COUNT(n) AS count LIMIT 1")
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def ensure_constraints(self) -> None:
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        self._execute(
            """
            CREATE NODE TABLE IF NOT EXISTS OntologyNode(
                id STRING PRIMARY KEY,
                node_type STRING,
                space STRING,
                name STRING,
                description STRING,
                text STRING,
                payload STRING
            )
            """,
            dict_rows=False,
        )
        for relation in all_relations():
            self._validate_identifier(relation)
            self._execute(
                f"CREATE REL TABLE IF NOT EXISTS {relation}(FROM OntologyNode TO OntologyNode, payload STRING)",  # noqa: S608
                dict_rows=False,
            )

    # ------------------------------------------------------------------
    # Node operations
    # ------------------------------------------------------------------

    def upsert_node(
        self,
        node_type: str,
        node_id: str,
        properties: dict[str, Any],
        space_id: str | None = None,
    ) -> dict[str, Any]:
        if not self._available:
            raise RuntimeError("LadybugStore is not available.")

        payload = {
            **properties,
            "id": node_id,
            "space": space_id or properties.get("space"),
            "node_type": node_type,
        }
        requested_space = str(space_id or properties.get("space") or "")
        existing = self._get_existing_identity(node_id)
        if existing is not None:
            existing_type = str(existing.get("node_type") or "")
            existing_space = str(existing.get("space") or "")
            if existing_type != node_type or existing_space != requested_space:
                raise ValueError(
                    "node_id "
                    f"{node_id!r} already exists as {existing_space or '?'}"
                    f"/{existing_type or '?'}; node ids must stay globally unique."
                )
        self._execute(
            """
            MERGE (n:OntologyNode {id: $id})
            SET n.node_type = $node_type,
                n.space = $space,
                n.name = $name,
                n.description = $description,
                n.text = $text,
                n.payload = $payload
            """,
            {
                "id": node_id,
                "node_type": node_type,
                "space": space_id or properties.get("space", ""),
                "name": str(properties.get("name") or ""),
                "description": str(properties.get("description") or properties.get("summary") or ""),
                "text": str(
                    properties.get("text")
                    or properties.get("message")
                    or properties.get("statement")
                    or properties.get("summary")
                    or ""
                ),
                "payload": self._json_dump(payload),
            },
            dict_rows=False,
        )
        return payload

    def get_node(self, node_type: str, node_id: str) -> dict[str, Any] | None:
        rows = self._execute_dict_rows(
            """
            MATCH (n:OntologyNode {id: $id})
            WHERE n.node_type = $node_type
            RETURN n.payload AS payload
            LIMIT 1
            """,
            {"id": node_id, "node_type": node_type},
        )
        if not rows:
            return None
        return self._decode_payload(rows[0].get("payload"))

    def delete_node(self, node_type: str, node_id: str) -> bool:
        del node_type  # node ids are unique across the local embedded graph.
        if not self._available:
            raise RuntimeError("LadybugStore is not available.")
        rows = self._execute(
            """
            MATCH (n:OntologyNode {id: $id})
            DELETE n
            RETURN $id AS deleted_id
            """,
            {"id": node_id},
        )
        return bool(rows)

    # ------------------------------------------------------------------
    # Edge operations
    # ------------------------------------------------------------------

    def upsert_edge(
        self,
        from_type: str,
        from_id: str,
        relation: str,
        to_type: str,
        to_id: str,
        properties: dict[str, Any] | None = None,
    ) -> bool:
        del from_type, to_type  # local embedded graph stores node_type on the node itself
        if not self._available:
            raise RuntimeError("LadybugStore is not available.")

        self._validate_identifier(relation)
        exists = self._execute(
            """
            MATCH (a:OntologyNode {id: $from_id}), (b:OntologyNode {id: $to_id})
            RETURN a.id AS from_id, b.id AS to_id
            LIMIT 1
            """,
            {"from_id": from_id, "to_id": to_id},
        )
        if not exists:
            return False

        self._execute(
            f"""
            MATCH (a:OntologyNode {{id: $from_id}}), (b:OntologyNode {{id: $to_id}})
            MERGE (a)-[r:{relation}]->(b)
            SET r.payload = $payload
            """,  # noqa: S608
            {
                "from_id": from_id,
                "to_id": to_id,
                "payload": self._json_dump(properties or {}),
            },
            dict_rows=False,
        )
        return True

    # ------------------------------------------------------------------
    # Query operations
    # ------------------------------------------------------------------

    def run_cypher(
        self, cypher: str, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Execute the OpenCrab runtime's Cypher subset against LadybugDB."""
        if not self._available:
            raise RuntimeError("LadybugStore is not available.")

        if "properties(group).id AS group_id" in cypher:
            return self._run_transitive_access_query(cypher, params or {})
        if "RETURN type(r) AS rel_type" in cypher and "group_id" not in cypher:
            return self._run_direct_access_query(cypher, params or {})

        translated = self._translate_runtime_cypher(cypher)
        rows = self._execute_dict_rows(translated, params or {})
        return [self._postprocess_row(row) for row in rows]

    def find_neighbors(
        self,
        node_id: str,
        direction: str = "both",
        depth: int = 1,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        if not self._available:
            raise RuntimeError("LadybugStore is not available.")

        visited: set[str] = {node_id}
        queue: deque[tuple[str, int]] = deque([(node_id, 0)])
        results: list[dict[str, Any]] = []

        with self._connection() as conn:
            while queue and len(results) < limit:
                current_id, current_depth = queue.popleft()
                if current_depth >= depth:
                    continue

                for neighbor in self._adjacent_nodes(current_id, direction, conn=conn):
                    nid = str(neighbor["node_id"])
                    if nid in visited:
                        continue
                    visited.add(nid)
                    results.append(
                        {
                            "properties": self._properties_from_row(neighbor),
                            "labels": [neighbor.get("node_type")],
                        }
                    )
                    queue.append((nid, current_depth + 1))
                    if len(results) >= limit:
                        break

        return results

    def find_path(
        self, from_id: str, to_id: str, max_depth: int = 4
    ) -> list[dict[str, Any]]:
        if not self._available:
            raise RuntimeError("LadybugStore is not available.")

        visited: set[str] = {from_id}
        queue: deque[tuple[str, list[dict[str, Any]]]] = deque([(from_id, [])])

        with self._connection() as conn:
            while queue:
                current_id, path = queue.popleft()
                if len(path) >= max_depth * 2:
                    continue

                for neighbor in self._adjacent_nodes(
                    current_id,
                    direction="out",
                    conn=conn,
                ):
                    nid = str(neighbor["node_id"])
                    rel = str(neighbor["rel_type"])
                    node = self._properties_from_row(neighbor)
                    new_path = path + [{"node": node, "relation": rel}]

                    if nid == to_id:
                        return new_path

                    if nid not in visited:
                        visited.add(nid)
                        queue.append((nid, new_path))

        return []

    def count_nodes(self, node_type: str | None = None) -> int:
        if not self._available:
            raise RuntimeError("LadybugStore is not available.")

        if node_type:
            rows = self._execute_dict_rows(
                """
                MATCH (n:OntologyNode)
                WHERE n.node_type = $node_type
                RETURN COUNT(n) AS count
                """,
                {"node_type": node_type},
            )
        else:
            rows = self._execute_dict_rows(
                "MATCH (n:OntologyNode) RETURN COUNT(n) AS count"
            )
        return int(rows[0]["count"]) if rows else 0

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _execute(
        self,
        query: str,
        params: dict[str, Any] | None = None,
        *,
        dict_rows: bool = True,
        conn: Any | None = None,
    ) -> list[dict[str, Any]] | list[list[Any]]:
        if conn is not None:
            result = conn.execute(query, params or {})
            try:
                if hasattr(result, "rows_as_dict") and dict_rows:
                    return result.rows_as_dict().get_all()
                if hasattr(result, "get_all"):
                    return result.get_all()
                return list(result)
            finally:
                close = getattr(result, "close", None)
                if callable(close):
                    try:
                        close()
                    except Exception:
                        pass

        with self._connection() as conn:
            result = conn.execute(query, params or {})
            try:
                if hasattr(result, "rows_as_dict") and dict_rows:
                    return result.rows_as_dict().get_all()
                if hasattr(result, "get_all"):
                    return result.get_all()
                return list(result)
            finally:
                close = getattr(result, "close", None)
                if callable(close):
                    try:
                        close()
                    except Exception:
                        pass

    def _execute_dict_rows(
        self,
        query: str,
        params: dict[str, Any] | None = None,
        *,
        conn: Any | None = None,
    ) -> list[dict[str, Any]]:
        return cast(
            list[dict[str, Any]],
            self._execute(query, params=params, dict_rows=True, conn=conn),
        )

    @contextmanager
    def _connection(self) -> Any:
        if self._lb is None:
            raise RuntimeError("LadybugStore is not available.")

        with self._op_lock:
            db, conn = self._open_handles()
            try:
                yield conn
            finally:
                for resource in (conn, db):
                    close = getattr(resource, "close", None)
                    if callable(close):
                        try:
                            close()
                        except Exception:
                            pass

    def _open_handles(self) -> tuple[Any, Any]:
        if self._lb is None:
            raise RuntimeError("LadybugStore is not available.")

        last_exc: Exception | None = None
        for attempt in range(5):
            try:
                db = self._lb.Database(self._db_path)
                conn = self._lb.Connection(db)
                return db, conn
            except Exception as exc:
                last_exc = exc
                if "Could not set lock on file" not in str(exc) or attempt == 4:
                    raise
                time.sleep(0.05 * (attempt + 1))

        assert last_exc is not None
        raise last_exc

    def _translate_runtime_cypher(self, cypher: str) -> str:
        translated = cypher
        translated = re.sub(r"labels\((\w+)\)\[0\]", r"\1.node_type", translated)
        translated = re.sub(r"type\((\w+)\)", r"label(\1)", translated)
        translated = re.sub(r"properties\((\w+)\)\.id", r"\1.id", translated)
        translated = re.sub(r"properties\((\w+)\)", r"\1.payload", translated)
        return translated

    def _postprocess_row(self, row: dict[str, Any]) -> dict[str, Any]:
        processed: dict[str, Any] = {}
        for key, value in row.items():
            if isinstance(value, str) and (key == "props" or key.endswith("Props") or key == "payload"):
                processed[key] = self._decode_payload(value)
            else:
                processed[key] = value
        return processed

    def _adjacent_nodes(
        self,
        node_id: str,
        direction: str,
        *,
        conn: Any | None = None,
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        if direction in ("out", "both"):
            rows.extend(
                self._execute_dict_rows(
                    """
                    MATCH (n:OntologyNode {id: $id})-[r]->(m)
                    RETURN label(r) AS rel_type,
                           m.id AS node_id,
                           m.node_type AS node_type,
                           m.space AS space,
                           m.name AS name,
                           m.description AS description,
                           m.text AS text,
                           m.payload AS payload
                    """,
                    {"id": node_id},
                    conn=conn,
                )
            )
        if direction in ("in", "both"):
            rows.extend(
                self._execute_dict_rows(
                    """
                    MATCH (m)-[r]->(n:OntologyNode {id: $id})
                    RETURN label(r) AS rel_type,
                           m.id AS node_id,
                           m.node_type AS node_type,
                           m.space AS space,
                           m.name AS name,
                           m.description AS description,
                           m.text AS text,
                           m.payload AS payload
                    """,
                    {"id": node_id},
                    conn=conn,
                )
            )
        return rows

    def _decode_payload(self, payload: Any) -> dict[str, Any]:
        if isinstance(payload, dict):
            return payload
        if not isinstance(payload, str) or not payload:
            return {}
        try:
            decoded = base64.b64decode(payload.encode()).decode()
            return json.loads(decoded)
        except Exception:
            pass
        try:
            return json.loads(payload)
        except json.JSONDecodeError:
            value = ast.literal_eval(payload)
            return value if isinstance(value, dict) else {}

    def _json_dump(self, payload: dict[str, Any]) -> str:
        raw = json.dumps(payload, ensure_ascii=False, default=str).encode()
        return base64.b64encode(raw).decode()

    def _validate_identifier(self, name: str) -> None:
        if not _SAFE_IDENTIFIER.match(name):
            raise ValueError(f"Unsafe Ladybug identifier: {name!r}")

    def _run_direct_access_query(
        self, cypher: str, params: dict[str, Any]
    ) -> list[dict[str, Any]]:
        relation_match = re.search(r"-\[r:([A-Za-z0-9_|]+)\]->", cypher)
        allowed_relations = set((relation_match.group(1) if relation_match else "").split("|"))
        rows = self._execute_dict_rows(
            """
            MATCH (s:OntologyNode {id: $sid})-[r]->(res:OntologyNode {id: $rid})
            RETURN label(r) AS rel_type
            """,
            {"sid": params.get("sid"), "rid": params.get("rid")},
        )
        filtered = [row for row in rows if row.get("rel_type") in allowed_relations]
        return filtered[:1]

    def _run_transitive_access_query(
        self, cypher: str, params: dict[str, Any]
    ) -> list[dict[str, Any]]:
        membership_match = re.search(r"-\[:([A-Za-z0-9_|]+)\]->\(group\)", cypher)
        resource_match = re.search(r"\(group\)-\[r:([A-Za-z0-9_|]+)\]->", cypher)
        membership_relations = set((membership_match.group(1) if membership_match else "").split("|"))
        resource_relations = set((resource_match.group(1) if resource_match else "").split("|"))

        rows = self._execute_dict_rows(
            """
            MATCH (s:OntologyNode {id: $sid})-[m]->(grp:OntologyNode)
            MATCH (grp:OntologyNode)-[r]->(res:OntologyNode {id: $rid})
            RETURN label(m) AS membership_rel, label(r) AS rel_type, grp.id AS group_id
            """,
            {"sid": params.get("sid"), "rid": params.get("rid")},
        )
        filtered = [
            {
                "rel_type": row["rel_type"],
                "group_id": row["group_id"],
            }
            for row in rows
            if row.get("membership_rel") in membership_relations
            and row.get("rel_type") in resource_relations
        ]
        return filtered[:1]

    def _properties_from_row(self, row: dict[str, Any]) -> dict[str, Any]:
        props = self._decode_payload(row.get("payload"))
        props.setdefault("id", row.get("node_id"))
        props.setdefault("space", row.get("space"))
        props.setdefault("node_type", row.get("node_type"))
        if row.get("name"):
            props.setdefault("name", row.get("name"))
        if row.get("description"):
            props.setdefault("description", row.get("description"))
        if row.get("text"):
            props.setdefault("text", row.get("text"))
        return props

    def _get_existing_identity(self, node_id: str) -> dict[str, Any] | None:
        rows = self._execute_dict_rows(
            """
            MATCH (n:OntologyNode {id: $id})
            RETURN n.node_type AS node_type, n.space AS space
            LIMIT 1
            """,
            {"id": node_id},
        )
        return rows[0] if rows else None
