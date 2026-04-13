from __future__ import annotations

from fastapi.testclient import TestClient


def _reset_runtime() -> None:
    from opencrab.config import reset_settings_cache
    from opencrab.mcp.tools import reset_runtime_state
    from opencrab.stores.factory import reset_store_caches

    reset_runtime_state()
    reset_settings_cache()
    reset_store_caches()


def _seed_local_runtime(tmp_path):
    from opencrab.config import Settings
    from opencrab.ontology.builder import OntologyBuilder
    from opencrab.ontology.query import HybridQuery
    from opencrab.stores.factory import make_runtime_stores

    settings = Settings(
        STORAGE_MODE="local",
        LOCAL_DATA_DIR=str(tmp_path / "opencrab_data"),
        CHROMA_COLLECTION="local_api_test",
        CHROMA_EMBEDDING_PROVIDER="onnx",
    )
    stores = make_runtime_stores(settings)
    builder = OntologyBuilder(stores.graph, stores.documents, stores.sql)
    builder.add_node("subject", "User", "u1", {"name": "Alice"})
    builder.add_node("resource", "Document", "doc1", {"name": "Spec"})
    builder.add_edge("subject", "u1", "owns", "resource", "doc1")
    HybridQuery(stores.vector, stores.graph).ingest(
        text="Cache TTL improves reliability for doc1.",
        source_id="doc://1",
        metadata={"space": "resource", "node_id": "doc1"},
    )
    stores.documents.upsert_source(
        "doc://1",
        "Cache TTL improves reliability for doc1.",
        {"space": "resource", "node_id": "doc1"},
    )


def test_local_api_status_nodes_edges_query_and_node_detail(monkeypatch, tmp_path):
    _reset_runtime()
    monkeypatch.setenv("STORAGE_MODE", "local")
    monkeypatch.setenv("LOCAL_DATA_DIR", str(tmp_path / "opencrab_data"))
    monkeypatch.setenv("CHROMA_COLLECTION", "local_api_test")
    monkeypatch.setenv("CHROMA_EMBEDDING_PROVIDER", "onnx")

    _seed_local_runtime(tmp_path)

    from opencrab.web_api import app

    client = TestClient(app)

    status = client.get("/api/status")
    assert status.status_code == 200
    assert status.json()["ok"] is True
    assert status.json()["stores"]["graph"] is True

    nodes = client.get("/api/nodes")
    assert nodes.status_code == 200
    node_ids = {node["id"] for node in nodes.json()["nodes"]}
    assert {"u1", "doc1"}.issubset(node_ids)

    edges = client.get("/api/edges")
    assert edges.status_code == 200
    edge_payload = edges.json()["edges"]
    assert any(edge["from_id"] == "u1" and edge["to_id"] == "doc1" for edge in edge_payload)

    query = client.post("/api/query", json={"question": "cache ttl reliability", "limit": 5})
    assert query.status_code == 200
    assert query.json()["total"] >= 1
    assert "context" in query.json()

    detail = client.get("/api/node/doc1")
    assert detail.status_code == 200
    assert detail.json()["id"] == "doc1"
    assert detail.json()["properties"]["name"] == "Spec"

    missing = client.get("/api/node/missing")
    assert missing.status_code == 404
