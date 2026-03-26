"""Local-first store and runtime tests for little-crab."""

from __future__ import annotations

import subprocess
import sys

import pytest


class TestLadybugStoreUnit:
    @pytest.fixture
    def store(self, tmp_path):
        from opencrab.stores.ladybug_store import LadybugStore

        return LadybugStore(str(tmp_path / "graph.lbug"))

    def test_upsert_node_and_runtime_lookup(self, store):
        store.upsert_node("User", "u1", {"name": "Alice"}, space_id="subject")

        rows = store.run_cypher(
            "MATCH (n {id: $id}) RETURN labels(n)[0] AS lbl, n.space AS space LIMIT 1",
            {"id": "u1"},
        )

        assert rows == [{"lbl": "User", "space": "subject"}]

    def test_upsert_node_rejects_cross_space_id_reuse(self, store):
        store.upsert_node("User", "shared-id", {"name": "Alice"}, space_id="subject")

        with pytest.raises(ValueError, match="globally unique"):
            store.upsert_node(
                "Document",
                "shared-id",
                {"name": "Spec"},
                space_id="resource",
            )

    def test_multiple_store_instances_can_open_same_db(self, tmp_path):
        from opencrab.stores.ladybug_store import LadybugStore

        db_path = str(tmp_path / "graph.lbug")
        first = LadybugStore(db_path)
        second = LadybugStore(db_path)

        assert first.available is True
        assert second.available is True

    def test_upsert_edge_neighbors_and_path(self, store):
        store.upsert_node("User", "u1", {"name": "Alice"}, space_id="subject")
        store.upsert_node("Team", "t1", {"name": "Data Team"}, space_id="subject")
        store.upsert_node("Project", "p1", {"name": "Project"}, space_id="resource")

        assert store.upsert_edge("User", "u1", "member_of", "Team", "t1") is True
        assert store.upsert_edge("Team", "t1", "can_view", "Project", "p1") is True

        neighbors = store.find_neighbors("u1", direction="both", depth=2, limit=10)
        neighbor_ids = {n["properties"]["id"] for n in neighbors}
        assert "t1" in neighbor_ids
        assert "p1" in neighbor_ids

        path = store.find_path("u1", "p1", max_depth=3)
        assert len(path) == 2
        assert path[-1]["node"]["id"] == "p1"

    def test_runtime_queries_for_rebac_and_lever_paths(self, store):
        store.upsert_node("User", "u1", {"name": "Alice"}, space_id="subject")
        store.upsert_node("Team", "t1", {"name": "Data Team"}, space_id="subject")
        store.upsert_node("Project", "p1", {"name": "Project"}, space_id="resource")
        store.upsert_node("Lever", "l1", {"name": "Cache TTL"}, space_id="lever")
        store.upsert_node("Outcome", "o1", {"name": "Reliability"}, space_id="outcome")
        store.upsert_node("Concept", "c1", {"name": "Performance"}, space_id="concept")

        store.upsert_edge("User", "u1", "member_of", "Team", "t1")
        store.upsert_edge("Team", "t1", "can_view", "Project", "p1")
        store.upsert_edge("Lever", "l1", "raises", "Outcome", "o1")
        store.upsert_edge("Lever", "l1", "affects", "Concept", "c1")

        transitive = store.run_cypher(
            """
            MATCH (s {id: $sid})-[:member_of|manages]->(group)-[r:can_view|can_edit|can_approve|owns|manages]->(res {id: $rid})
            RETURN type(r) AS rel_type, properties(group).id AS group_id
            LIMIT 1
            """,
            {"sid": "u1", "rid": "p1"},
        )
        assert transitive[0]["rel_type"] == "can_view"
        assert transitive[0]["group_id"] == "t1"

        lever_rows = store.run_cypher(
            """
            MATCH (l {id: $lid})-[r:raises|lowers|stabilizes|optimizes]->(o)
            RETURN properties(o) AS oProps, type(r) AS rType, labels(o)[0] AS oLabel
            LIMIT 20
            """,
            {"lid": "l1"},
        )
        assert lever_rows[0]["rType"] == "raises"
        assert lever_rows[0]["oProps"]["id"] == "o1"
        assert lever_rows[0]["oLabel"] == "Outcome"


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

    def test_factory_uses_embedded_chroma_path(self, tmp_path):
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

    def test_second_process_can_open_same_db_file(self, tmp_path):
        from opencrab.stores.duckdb_store import DuckDBStore

        db_path = tmp_path / "opencrab.db"
        store = DuckDBStore(str(db_path))
        store.upsert_node_doc("subject", "User", "u1", {"name": "Alice"})

        script = f"""
from opencrab.stores.duckdb_store import DuckDBStore
store = DuckDBStore(r\"{db_path}\")
print(store.available)
print(store.ping())
"""
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            check=True,
            cwd=str(tmp_path),
        )

        lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        assert lines[:2] == ["True", "True"]


class TestLocalFactory:
    def test_factory_returns_duckdb_store_for_doc_and_sql(self, tmp_path):
        from opencrab.config import Settings
        from opencrab.stores.duckdb_store import DuckDBStore
        from opencrab.stores.factory import make_doc_store, make_sql_store

        settings = Settings(STORAGE_MODE="local", LOCAL_DATA_DIR=str(tmp_path))

        docs = make_doc_store(settings)
        sql = make_sql_store(settings)

        assert isinstance(docs, DuckDBStore)
        assert isinstance(sql, DuckDBStore)
        assert docs is sql

    def test_factory_returns_ladybug_graph_store(self, tmp_path):
        from opencrab.config import Settings
        from opencrab.stores.factory import make_graph_store
        from opencrab.stores.ladybug_store import LadybugStore

        settings = Settings(STORAGE_MODE="local", LOCAL_DATA_DIR=str(tmp_path))
        graph = make_graph_store(settings)

        assert isinstance(graph, LadybugStore)
        assert graph.available is True

    def test_factory_reuses_ladybug_graph_store(self, tmp_path):
        from opencrab.config import Settings
        from opencrab.stores.factory import make_graph_store

        settings = Settings(STORAGE_MODE="local", LOCAL_DATA_DIR=str(tmp_path))

        first = make_graph_store(settings)
        second = make_graph_store(settings)

        assert first is second
        assert first.available is True


class TestLocalRuntime:
    def test_builder_persists_docs_registry_and_audit(self, tmp_path):
        from opencrab.ontology.builder import OntologyBuilder
        from opencrab.stores.duckdb_store import DuckDBStore
        from opencrab.stores.ladybug_store import LadybugStore

        graph = LadybugStore(str(tmp_path / "graph.lbug"))
        store = DuckDBStore(str(tmp_path / "opencrab.db"))
        builder = OntologyBuilder(graph, store, store)

        result = builder.add_node("subject", "User", "u1", {"name": "Alice"})

        assert result["stores"]["documents"].startswith("ok")
        assert result["stores"]["registry"] == "ok"
        assert result["stores"]["graph"] == "ok"
        assert store.get_node_doc("subject", "u1") is not None
        assert store.table_counts()["ontology_nodes"] == 1
        assert len(store.get_audit_log()) == 1

    def test_rebac_and_impact_persist_through_duckdb_store(self, tmp_path):
        from opencrab.ontology.impact import ImpactEngine
        from opencrab.ontology.rebac import ReBACEngine
        from opencrab.stores.duckdb_store import DuckDBStore
        from opencrab.stores.ladybug_store import LadybugStore

        graph = LadybugStore(str(tmp_path / "graph.lbug"))
        sql = DuckDBStore(str(tmp_path / "opencrab.db"))

        rebac = ReBACEngine(graph, sql)
        rebac.grant("u1", "view", "doc1")
        assert rebac.check("u1", "view", "doc1").granted is True

        impact = ImpactEngine(graph, sql)
        impact.analyse("u1", "update")
        assert len(sql.get_impacts("u1")) == 1

    def test_builder_rejects_duplicate_node_id_across_spaces(self, tmp_path):
        from opencrab.ontology.builder import OntologyBuilder
        from opencrab.stores.duckdb_store import DuckDBStore
        from opencrab.stores.ladybug_store import LadybugStore

        graph = LadybugStore(str(tmp_path / "graph.lbug"))
        store = DuckDBStore(str(tmp_path / "opencrab.db"))
        builder = OntologyBuilder(graph, store, store)

        builder.add_node("subject", "User", "shared-id", {"name": "Alice"})

        with pytest.raises(ValueError, match="globally unique"):
            builder.add_node("resource", "Document", "shared-id", {"name": "Spec"})

        assert store.get_node_doc("subject", "shared-id") is not None
        assert store.get_node_doc("resource", "shared-id") is None

    def test_rebac_impact_and_keyword_query_work(self, tmp_path):
        from opencrab.ontology.impact import ImpactEngine
        from opencrab.ontology.query import HybridQuery
        from opencrab.ontology.rebac import ReBACEngine
        from opencrab.stores.chroma_store import ChromaStore
        from opencrab.stores.duckdb_store import DuckDBStore
        from opencrab.stores.ladybug_store import LadybugStore

        graph = LadybugStore(str(tmp_path / "graph.lbug"))
        sql = DuckDBStore(str(tmp_path / "opencrab.db"))
        vector = ChromaStore(
            host="localhost",
            port=8000,
            collection_name="test_little_crab_vectors",
            local_mode=True,
            local_path=str(tmp_path / "chroma"),
        )

        graph.upsert_node("User", "u1", {"name": "Alice Analyst"}, space_id="subject")
        graph.upsert_node("Team", "t1", {"name": "Data Team"}, space_id="subject")
        graph.upsert_node("Project", "p1", {"name": "Analytics Project"}, space_id="resource")
        graph.upsert_node("Lever", "l1", {"name": "Cache TTL"}, space_id="lever")
        graph.upsert_node("Outcome", "o1", {"name": "Reliability"}, space_id="outcome")

        graph.upsert_edge("User", "u1", "member_of", "Team", "t1")
        graph.upsert_edge("Team", "t1", "can_view", "Project", "p1")
        graph.upsert_edge("Lever", "l1", "raises", "Outcome", "o1")

        rebac = ReBACEngine(graph, sql)
        decision = rebac.check("u1", "view", "p1")
        assert decision.granted is True
        assert "Transitive access" in decision.reason

        impact = ImpactEngine(graph, sql)
        result = impact.analyse("l1", "update")
        assert result.node_id == "l1"
        assert len(sql.get_impacts("l1")) == 1

        hybrid = HybridQuery(vector, graph)
        keyword_results = hybrid.keyword_search("analytics", spaces=["resource"], limit=5)
        assert len(keyword_results) == 1
        assert keyword_results[0]["node"]["id"] == "p1"
