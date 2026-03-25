"""
Tests for store adapters.

Tests that require live services are marked with pytest.mark.integration
and skipped by default. Unit-level tests (connection failures, sanitization,
etc.) run without any services.
"""

from __future__ import annotations

import json
import os
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

INTEGRATION = pytest.mark.skipif(
    os.environ.get("OPENCRAB_INTEGRATION") != "1",
    reason="Integration tests require OPENCRAB_INTEGRATION=1 and live services.",
)


# ---------------------------------------------------------------------------
# Neo4j store unit tests (no live DB)
# ---------------------------------------------------------------------------


class TestNeo4jStoreUnit:
    def test_unavailable_when_connection_fails(self):
        from opencrab.stores.neo4j_store import Neo4jStore

        store = Neo4jStore("bolt://invalid-host:7687", "neo4j", "password")
        assert store.available is False

    def test_ping_returns_false_when_unavailable(self):
        from opencrab.stores.neo4j_store import Neo4jStore

        store = Neo4jStore("bolt://invalid-host:7687", "neo4j", "password")
        assert store.ping() is False

    def test_upsert_node_raises_when_unavailable(self):
        from opencrab.stores.neo4j_store import Neo4jStore

        store = Neo4jStore("bolt://invalid-host:7687", "neo4j", "password")
        with pytest.raises(RuntimeError, match="not available"):
            store.upsert_node("User", "u1", {})

    def test_upsert_edge_raises_when_unavailable(self):
        from opencrab.stores.neo4j_store import Neo4jStore

        store = Neo4jStore("bolt://invalid-host:7687", "neo4j", "password")
        with pytest.raises(RuntimeError, match="not available"):
            store.upsert_edge("User", "u1", "owns", "Project", "p1")

    def test_run_cypher_raises_when_unavailable(self):
        from opencrab.stores.neo4j_store import Neo4jStore

        store = Neo4jStore("bolt://invalid-host:7687", "neo4j", "password")
        with pytest.raises(RuntimeError, match="not available"):
            store.run_cypher("RETURN 1")


# ---------------------------------------------------------------------------
# ChromaDB store unit tests
# ---------------------------------------------------------------------------


class TestChromaStoreUnit:
    def test_unavailable_when_connection_fails(self):
        from opencrab.stores.chroma_store import ChromaStore

        store = ChromaStore("invalid-host", 9999, "test_collection")
        assert store.available is False

    def test_ping_returns_false_when_unavailable(self):
        from opencrab.stores.chroma_store import ChromaStore

        store = ChromaStore("invalid-host", 9999, "test_collection")
        assert store.ping() is False

    def test_add_texts_raises_when_unavailable(self):
        from opencrab.stores.chroma_store import ChromaStore

        store = ChromaStore("invalid-host", 9999, "test_collection")
        with pytest.raises(RuntimeError, match="not available"):
            store.add_texts(["hello world"])

    def test_query_raises_when_unavailable(self):
        from opencrab.stores.chroma_store import ChromaStore

        store = ChromaStore("invalid-host", 9999, "test_collection")
        with pytest.raises(RuntimeError, match="not available"):
            store.query("test query")

    def test_count_returns_zero_when_unavailable(self):
        from opencrab.stores.chroma_store import ChromaStore

        store = ChromaStore("invalid-host", 9999, "test_collection")
        assert store.count() == 0

    def test_factory_uses_embedded_chroma_path_in_local_mode(self, tmp_path):
        from opencrab.config import Settings
        from opencrab.stores.chroma_store import ChromaStore
        from opencrab.stores.factory import make_vector_store

        settings = Settings(STORAGE_MODE="local", LOCAL_DATA_DIR=str(tmp_path))
        store = make_vector_store(settings)

        assert isinstance(store, ChromaStore)
        assert store.mode == "embedded"
        assert store.location == str(tmp_path / "chroma")

    def test_sanitize_metadata(self):
        from opencrab.stores.chroma_store import _sanitize_metadata

        meta = {
            "str_val": "hello",
            "int_val": 42,
            "float_val": 3.14,
            "bool_val": True,
            "none_val": None,
            "list_val": [1, 2, 3],
            "dict_val": {"nested": "obj"},
        }
        cleaned = _sanitize_metadata(meta)
        assert cleaned["str_val"] == "hello"
        assert cleaned["int_val"] == 42
        assert cleaned["float_val"] == 3.14
        assert cleaned["bool_val"] is True
        assert cleaned["none_val"] == ""
        assert cleaned["list_val"] == "[1, 2, 3]"
        assert cleaned["dict_val"] == "{'nested': 'obj'}"


# ---------------------------------------------------------------------------
# MongoDB store unit tests
# ---------------------------------------------------------------------------


class TestMongoStoreUnit:
    def test_unavailable_when_connection_fails(self):
        from opencrab.stores.mongo_store import MongoStore

        store = MongoStore("mongodb://invalid-host:27017", "testdb")
        assert store.available is False

    def test_ping_returns_false_when_unavailable(self):
        from opencrab.stores.mongo_store import MongoStore

        store = MongoStore("mongodb://invalid-host:27017", "testdb")
        assert store.ping() is False

    def test_log_event_silently_ignored_when_unavailable(self):
        from opencrab.stores.mongo_store import MongoStore

        store = MongoStore("mongodb://invalid-host:27017", "testdb")
        # Should not raise
        store.log_event("test_event", "u1", {"detail": "value"})

    def test_collection_stats_empty_when_unavailable(self):
        from opencrab.stores.mongo_store import MongoStore

        store = MongoStore("mongodb://invalid-host:27017", "testdb")
        stats = store.collection_stats()
        assert stats == {}

    def test_upsert_node_doc_raises_when_unavailable(self):
        from opencrab.stores.mongo_store import MongoStore

        store = MongoStore("mongodb://invalid-host:27017", "testdb")
        with pytest.raises(RuntimeError, match="not available"):
            store.upsert_node_doc("subject", "User", "u1", {"name": "Alice"})


# ---------------------------------------------------------------------------
# Local document store unit tests
# ---------------------------------------------------------------------------


class TestLocalDocStoreUnit:
    @pytest.fixture
    def store(self, tmp_path):
        from opencrab.stores.local_doc_store import LocalDocStore

        return LocalDocStore(str(tmp_path / "docs"))

    def test_upsert_node_doc_builder_compat(self, store):
        doc_id = store.upsert_node_doc("subject", "User", "u1", {"name": "Alice"})
        assert doc_id == "subject::u1"

        doc = store.get_node_doc("subject", "u1")
        assert doc is not None
        assert doc["node_type"] == "User"
        assert doc["properties"]["name"] == "Alice"

    def test_log_event_accepts_builder_signature(self, store):
        store.log_event("node_upsert", subject_id=None, details={"node_id": "u1"})
        events = store.get_audit_log()
        assert len(events) == 1
        assert events[0]["event_type"] == "node_upsert"
        assert events[0]["details"]["node_id"] == "u1"

    def test_log_event_accepts_payload_shortcut(self, store):
        store.log_event("edge_upsert", {"from_id": "u1", "to_id": "p1"})
        events = store.get_audit_log()
        assert len(events) == 1
        assert events[0]["details"]["from_id"] == "u1"


# ---------------------------------------------------------------------------
# DuckDB store unit tests
# ---------------------------------------------------------------------------


class TestDuckDBStoreUnit:
    @pytest.fixture
    def store(self, tmp_path):
        from opencrab.stores.duckdb_store import DuckDBStore

        return DuckDBStore(str(tmp_path / "opencrab.db"))

    def test_connects_with_local_file(self, store):
        assert store.available is True
        assert store.ping() is True

    def test_upsert_node_doc_and_audit_log(self, store):
        doc_id = store.upsert_node_doc("subject", "User", "u1", {"name": "Alice"})
        assert doc_id == "subject::u1"

        doc = store.get_node_doc("subject", "u1")
        assert doc is not None
        assert doc["properties"]["name"] == "Alice"

        store.log_event("node_upsert", subject_id=None, details={"node_id": "u1"})
        events = store.get_audit_log()
        assert len(events) == 1
        assert events[0]["event_type"] == "node_upsert"

    def test_upsert_source_and_retrieve(self, store):
        source_id = store.upsert_source("src-1", "hello world", {"space": "evidence"})
        assert source_id == "src-1"

        source = store.get_source("src-1")
        assert source is not None
        assert source["text"] == "hello world"
        assert source["metadata"]["space"] == "evidence"

    def test_register_policy_and_analysis_records(self, store):
        store.register_node("subject", "User", "u1")
        store.register_edge("subject", "u1", "owns", "resource", "r1")

        store.set_policy("u1", "view", "r1", granted=True)
        assert store.check_policy("u1", "view", "r1") is True

        impact_id = store.save_impact("u1", "update", {"ok": True})
        sim_id = store.save_simulation("lever-1", "raises", 0.4, {"ok": True})
        assert impact_id >= 1
        assert sim_id >= 1

        impacts = store.get_impacts("u1")
        assert len(impacts) == 1
        assert impacts[0]["impact"]["ok"] is True

    def test_table_counts_include_document_and_registry_tables(self, store):
        store.upsert_node_doc("subject", "User", "u1", {"name": "Alice"})
        store.upsert_source("src-1", "hello world", {})
        store.log_event("node_upsert", {"node_id": "u1"})
        store.register_node("subject", "User", "u1")
        store.set_policy("u1", "view", "r1", granted=True)

        counts = store.table_counts()
        assert counts["node_documents"] == 1
        assert counts["source_documents"] == 1
        assert counts["audit_log"] == 1
        assert counts["ontology_nodes"] == 1
        assert counts["rebac_policies"] == 1


# ---------------------------------------------------------------------------
# SQL store unit tests (uses SQLite in-memory)
# ---------------------------------------------------------------------------


class TestSQLStoreUnit:
    @pytest.fixture
    def sql_store(self):
        from opencrab.stores.sql_store import SQLStore

        return SQLStore("sqlite:///:memory:")

    def test_connects_with_sqlite(self, sql_store):
        assert sql_store.available is True

    def test_ping_returns_true_with_sqlite(self, sql_store):
        assert sql_store.ping() is True

    def test_register_node(self, sql_store):
        # Should not raise
        sql_store.register_node("subject", "User", "user-001")

    def test_register_node_idempotent(self, sql_store):
        sql_store.register_node("subject", "User", "user-002")
        sql_store.register_node("subject", "User", "user-002")  # duplicate OK

    def test_register_edge(self, sql_store):
        sql_store.register_node("subject", "User", "u1")
        sql_store.register_node("resource", "Project", "p1")
        sql_store.register_edge("subject", "u1", "owns", "resource", "p1")

    def test_register_edge_idempotent(self, sql_store):
        sql_store.register_node("subject", "User", "u2")
        sql_store.register_node("resource", "Project", "p2")
        sql_store.register_edge("subject", "u2", "owns", "resource", "p2")
        sql_store.register_edge("subject", "u2", "owns", "resource", "p2")  # duplicate OK

    def test_save_and_get_impact(self, sql_store):
        impact_data = {"triggered": [{"id": "I1", "name": "Data impact"}]}
        row_id = sql_store.save_impact("node-001", "update", impact_data)
        assert row_id >= 0

        records = sql_store.get_impacts("node-001")
        assert len(records) == 1
        assert records[0]["node_id"] == "node-001"
        assert records[0]["change_type"] == "update"
        assert records[0]["impact"]["triggered"][0]["id"] == "I1"

    def test_save_simulation(self, sql_store):
        results = {"lever_id": "lever-001", "predicted_outcome_changes": []}
        row_id = sql_store.save_simulation("lever-001", "raises", 0.8, results)
        assert row_id >= 0

    def test_set_and_check_policy_grant(self, sql_store):
        sql_store.set_policy("user-001", "view", "doc-001", granted=True)
        result = sql_store.check_policy("user-001", "view", "doc-001")
        assert result is True

    def test_set_and_check_policy_deny(self, sql_store):
        sql_store.set_policy("user-002", "edit", "doc-002", granted=False)
        result = sql_store.check_policy("user-002", "edit", "doc-002")
        assert result is False

    def test_check_policy_none_when_not_set(self, sql_store):
        result = sql_store.check_policy("unknown-user", "view", "unknown-resource")
        assert result is None

    def test_set_policy_overwrite(self, sql_store):
        sql_store.set_policy("u3", "approve", "r3", granted=True)
        sql_store.set_policy("u3", "approve", "r3", granted=False)
        result = sql_store.check_policy("u3", "approve", "r3")
        assert result is False

    def test_list_policies(self, sql_store):
        sql_store.set_policy("u4", "view", "r4", granted=True)
        sql_store.set_policy("u4", "edit", "r5", granted=True)
        policies = sql_store.list_policies("u4")
        assert len(policies) == 2
        permissions = {p["permission"] for p in policies}
        assert "view" in permissions
        assert "edit" in permissions

    def test_table_counts_returns_dict(self, sql_store):
        counts = sql_store.table_counts()
        assert isinstance(counts, dict)
        assert "ontology_nodes" in counts
        assert "rebac_policies" in counts


class TestLocalFactoryDuckDB:
    def test_local_factory_returns_duckdb_store_for_doc_and_sql(self, tmp_path):
        from opencrab.config import Settings
        from opencrab.stores.duckdb_store import DuckDBStore
        from opencrab.stores.factory import make_doc_store, make_sql_store

        settings = Settings(STORAGE_MODE="local", LOCAL_DATA_DIR=str(tmp_path))

        docs = make_doc_store(settings)
        sql = make_sql_store(settings)

        assert isinstance(docs, DuckDBStore)
        assert isinstance(sql, DuckDBStore)
        assert docs is sql


class TestDuckDBBackedRuntime:
    def test_builder_persists_docs_registry_and_audit_without_mongo_postgres(self, tmp_path):
        from opencrab.ontology.builder import OntologyBuilder
        from opencrab.stores.duckdb_store import DuckDBStore
        from opencrab.stores.neo4j_store import Neo4jStore

        graph = Neo4jStore("bolt://invalid:7687", "neo4j", "pw")
        store = DuckDBStore(str(tmp_path / "opencrab.db"))
        builder = OntologyBuilder(graph, store, store)

        result = builder.add_node("subject", "User", "u1", {"name": "Alice"})

        assert result["stores"]["mongodb"].startswith("ok")
        assert result["stores"]["postgres"] == "ok"
        assert store.get_node_doc("subject", "u1") is not None
        assert store.table_counts()["ontology_nodes"] == 1
        assert len(store.get_audit_log()) == 1

    def test_rebac_and_impact_persist_through_duckdb_store(self, tmp_path):
        from opencrab.ontology.impact import ImpactEngine
        from opencrab.ontology.rebac import ReBACEngine
        from opencrab.stores.duckdb_store import DuckDBStore
        from opencrab.stores.neo4j_store import Neo4jStore

        graph = Neo4jStore("bolt://invalid:7687", "neo4j", "pw")
        store = DuckDBStore(str(tmp_path / "opencrab.db"))

        rebac = ReBACEngine(graph, store)
        rebac.grant("u1", "view", "doc1")
        assert rebac.check("u1", "view", "doc1").granted is True

        impact = ImpactEngine(graph, store)
        impact.analyse("u1", "update")
        assert len(store.get_impacts("u1")) == 1

    def test_unavailable_store_raises(self):
        from opencrab.stores.sql_store import SQLStore

        store = SQLStore("postgresql://invalid:invalid@invalid-host:5432/invalid")
        assert store.available is False

    def test_ping_false_when_unavailable(self):
        from opencrab.stores.sql_store import SQLStore

        store = SQLStore("postgresql://invalid:invalid@invalid-host:5432/invalid")
        assert store.ping() is False


# ---------------------------------------------------------------------------
# Integration tests (require OPENCRAB_INTEGRATION=1)
# ---------------------------------------------------------------------------


@INTEGRATION
class TestNeo4jIntegration:
    @pytest.fixture
    def store(self):
        from opencrab.config import get_settings
        from opencrab.stores.neo4j_store import Neo4jStore

        cfg = get_settings()
        s = Neo4jStore(cfg.neo4j_uri, cfg.neo4j_user, cfg.neo4j_password)
        assert s.available, "Neo4j not available for integration test"
        return s

    def test_upsert_and_get_node(self, store):
        store.upsert_node("User", "test-u1", {"name": "Test User"}, space_id="subject")
        node = store.get_node("User", "test-u1")
        assert node is not None
        assert node["id"] == "test-u1"

    def test_delete_node(self, store):
        store.upsert_node("User", "test-u2", {"name": "Delete Me"})
        deleted = store.delete_node("User", "test-u2")
        assert deleted is True
        assert store.get_node("User", "test-u2") is None

    def test_count_nodes(self, store):
        count = store.count_nodes()
        assert isinstance(count, int)
        assert count >= 0
