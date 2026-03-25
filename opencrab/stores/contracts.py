"""
Backend-agnostic store contracts for OpenCrab.

These protocols capture the semantic seams the ontology runtime depends on
without tying the runtime to a specific backend implementation.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class GraphStore(Protocol):
    """Graph persistence and traversal contract."""

    @property
    def available(self) -> bool: ...

    def upsert_node(
        self,
        node_type: str,
        node_id: str,
        properties: dict[str, Any],
        space_id: str | None = None,
    ) -> dict[str, Any]: ...

    def upsert_edge(
        self,
        from_type: str,
        from_id: str,
        relation: str,
        to_type: str,
        to_id: str,
        properties: dict[str, Any] | None = None,
    ) -> bool: ...

    def run_cypher(
        self, cypher: str, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]: ...

    def find_neighbors(
        self,
        node_id: str,
        direction: str = "both",
        depth: int = 1,
        limit: int = 50,
    ) -> list[dict[str, Any]]: ...

    def find_path(
        self, from_id: str, to_id: str, max_depth: int = 4
    ) -> list[dict[str, Any]]: ...


@runtime_checkable
class DocStore(Protocol):
    """Document and source persistence contract."""

    @property
    def available(self) -> bool: ...

    def upsert_node_doc(
        self,
        space: str,
        node_type: str,
        node_id: str,
        properties: dict[str, Any],
    ) -> str: ...

    def get_node_doc(self, space: str, node_id: str) -> dict[str, Any] | None: ...

    def list_nodes(self, space: str | None = None) -> list[dict[str, Any]]: ...

    def upsert_source(
        self, source_id: str, text: str, metadata: dict[str, Any]
    ) -> str | None: ...

    def get_source(self, source_id: str) -> dict[str, Any] | None: ...

    def list_sources(self) -> list[dict[str, Any]]: ...


@runtime_checkable
class EventStore(Protocol):
    """Audit/event log contract."""

    @property
    def available(self) -> bool: ...

    def log_event(
        self,
        event_type: str,
        subject_id: str | dict[str, Any] | None = None,
        details: dict[str, Any] | None = None,
        actor: str = "system",
    ) -> None: ...


@runtime_checkable
class RegistryStore(Protocol):
    """Structural registry contract for nodes and edges."""

    @property
    def available(self) -> bool: ...

    def register_node(self, space: str, node_type: str, node_id: str) -> None: ...

    def register_edge(
        self, from_space: str, from_id: str, relation: str, to_space: str, to_id: str
    ) -> None: ...


@runtime_checkable
class PolicyStore(Protocol):
    """Relationship-based access policy contract."""

    @property
    def available(self) -> bool: ...

    def set_policy(
        self,
        subject_id: str,
        permission: str,
        resource_id: str,
        granted: bool = True,
    ) -> None: ...

    def check_policy(
        self, subject_id: str, permission: str, resource_id: str
    ) -> bool | None: ...

    def list_policies(self, subject_id: str) -> list[dict[str, Any]]: ...


@runtime_checkable
class AnalysisStore(Protocol):
    """Impact and simulation persistence contract."""

    @property
    def available(self) -> bool: ...

    def save_impact(
        self, node_id: str, change_type: str, impact: dict[str, Any]
    ) -> int: ...

    def save_simulation(
        self, lever_id: str, direction: str, magnitude: float, results: dict[str, Any]
    ) -> int: ...


@runtime_checkable
class VectorStore(Protocol):
    """Vector ingestion and search contract."""

    @property
    def available(self) -> bool: ...

    def upsert_texts(
        self,
        texts: list[str],
        metadatas: list[dict[str, Any]] | None = None,
        ids: list[str] | None = None,
    ) -> list[str]: ...

    def query(
        self,
        query_text: str,
        n_results: int = 10,
        where: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]: ...


@runtime_checkable
class DocumentEventStore(DocStore, EventStore, Protocol):
    """Combined doc and event contract used by the builder and ingest path."""


@runtime_checkable
class OperationalStore(RegistryStore, PolicyStore, AnalysisStore, Protocol):
    """Combined relational contract used across registry, policy, and analysis paths."""
