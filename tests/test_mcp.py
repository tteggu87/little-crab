"""
Tests for the MCP server and tool dispatcher.

All tests mock the underlying stores so no live services are required.
"""

from __future__ import annotations

import json
from io import StringIO
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Tool dispatcher tests
# ---------------------------------------------------------------------------


class TestToolDispatch:
    def test_dispatch_unknown_tool_raises(self):
        from opencrab.mcp.tools import dispatch_tool

        with pytest.raises(KeyError, match="Unknown tool"):
            dispatch_tool("nonexistent_tool", {})

    def test_tools_list_not_empty(self):
        from opencrab.mcp.tools import TOOLS

        assert len(TOOLS) == 9  # 9 tools defined (includes ontology_extract)
        names = [t["name"] for t in TOOLS]
        assert "ontology_manifest" in names
        assert "ontology_add_node" in names
        assert "ontology_add_edge" in names
        assert "ontology_query" in names
        assert "ontology_impact" in names
        assert "ontology_rebac_check" in names
        assert "ontology_lever_simulate" in names
        assert "ontology_ingest" in names

    def test_tools_have_required_schema_keys(self):
        from opencrab.mcp.tools import TOOLS

        for tool in TOOLS:
            assert "name" in tool
            assert "description" in tool
            assert "inputSchema" in tool
            schema = tool["inputSchema"]
            assert "type" in schema
            assert "properties" in schema

    def test_ontology_manifest_returns_grammar(self):
        from opencrab.mcp.tools import dispatch_tool

        result = dispatch_tool("ontology_manifest", {})
        assert "spaces" in result
        assert "meta_edges" in result
        assert "impact_categories" in result
        assert "rebac" in result

    def test_ontology_add_node_validation_error(self):
        """Adding a node with invalid space returns an error dict (no exception)."""
        from opencrab.mcp.tools import _context, dispatch_tool

        # Clear context so it re-initialises with mocked stores
        _context.clear()

        with patch("opencrab.mcp.tools._get_context") as mock_ctx:
            builder = MagicMock()
            builder.add_node.side_effect = ValueError("Unknown space 'badspace'.")
            mock_ctx.return_value = {"builder": builder, "rebac": MagicMock(), "impact": MagicMock(), "hybrid": MagicMock(), "documents": MagicMock()}

            result = dispatch_tool("ontology_add_node", {
                "space": "badspace", "node_type": "User", "node_id": "u1"
            })
            assert "error" in result
            assert result.get("valid") is False

    def test_ontology_add_node_success(self):
        from opencrab.mcp.tools import dispatch_tool

        with patch("opencrab.mcp.tools._get_context") as mock_ctx:
            builder = MagicMock()
            builder.add_node.return_value = {
                "node_id": "u1", "space": "subject", "node_type": "User",
                "properties": {}, "stores": {"graph": "ok"}
            }
            mock_ctx.return_value = {
                "builder": builder, "rebac": MagicMock(),
                "impact": MagicMock(), "hybrid": MagicMock(), "documents": MagicMock(),
            }
            result = dispatch_tool("ontology_add_node", {
                "space": "subject", "node_type": "User", "node_id": "u1"
            })
            assert result["node_id"] == "u1"
            assert "stores" in result

    def test_ontology_add_edge_success(self):
        from opencrab.mcp.tools import dispatch_tool

        with patch("opencrab.mcp.tools._get_context") as mock_ctx:
            builder = MagicMock()
            builder.add_edge.return_value = {
                "from": {"space": "subject", "id": "u1"},
                "relation": "owns",
                "to": {"space": "resource", "id": "doc1"},
                "stores": {"graph": "ok"},
            }
            mock_ctx.return_value = {
                "builder": builder, "rebac": MagicMock(),
                "impact": MagicMock(), "hybrid": MagicMock(), "documents": MagicMock(),
            }
            result = dispatch_tool("ontology_add_edge", {
                "from_space": "subject", "from_id": "u1",
                "relation": "owns",
                "to_space": "resource", "to_id": "doc1",
            })
            assert result["relation"] == "owns"

    def test_ontology_add_edge_invalid_relation(self):
        from opencrab.mcp.tools import dispatch_tool

        with patch("opencrab.mcp.tools._get_context") as mock_ctx:
            builder = MagicMock()
            builder.add_edge.side_effect = ValueError("Relation 'mentions' is not valid")
            mock_ctx.return_value = {
                "builder": builder, "rebac": MagicMock(),
                "impact": MagicMock(), "hybrid": MagicMock(), "documents": MagicMock(),
            }
            result = dispatch_tool("ontology_add_edge", {
                "from_space": "subject", "from_id": "u1",
                "relation": "mentions",
                "to_space": "resource", "to_id": "doc1",
            })
            assert "error" in result
            assert result.get("valid") is False

    def test_ontology_query_returns_results(self):
        from opencrab.mcp.tools import dispatch_tool
        from opencrab.ontology.context_pipeline import AgentContextBundle, AgentFact

        with patch("opencrab.mcp.tools._get_context") as mock_ctx:
            bundle = AgentContextBundle(
                facts=[
                    AgentFact(
                        source="vector",
                        node_id="n1",
                        score=0.9,
                        text="Test text",
                        metadata={},
                    )
                ],
                supporting_evidence=[],
                provenance_paths=[],
                inferred_links=[],
                missing_links=[],
                policies=[],
                scope={"graph_expansion_enabled": True},
                uncertainty={"fact_count": 1},
                raw_refs=[],
            )
            context_pipeline = MagicMock()
            context_pipeline.build_context.return_value = bundle
            mock_ctx.return_value = {
                "builder": MagicMock(), "rebac": MagicMock(),
                "impact": MagicMock(),
                "hybrid": MagicMock(),
                "documents": MagicMock(),
                "context_pipeline": context_pipeline,
            }
            result = dispatch_tool("ontology_query", {"question": "What is a lever?"})
            assert "results" in result
            assert "context" in result
            assert result["total"] == 1
            assert result["results"][0]["node_id"] == "n1"

    def test_ontology_impact_returns_analysis(self):
        from opencrab.mcp.tools import dispatch_tool
        from opencrab.ontology.impact import ImpactResult

        with patch("opencrab.mcp.tools._get_context") as mock_ctx:
            mock_impact = ImpactResult(
                node_id="n1", change_type="update", space="concept", node_type="Concept",
                triggered=[{"id": "I1", "name": "Data impact"}],
                summary="Test summary",
            )
            impact_engine = MagicMock()
            impact_engine.analyse.return_value = mock_impact
            mock_ctx.return_value = {
                "builder": MagicMock(), "rebac": MagicMock(),
                "impact": impact_engine, "hybrid": MagicMock(), "documents": MagicMock(),
            }
            result = dispatch_tool("ontology_impact", {"node_id": "n1", "change_type": "update"})
            assert result["node_id"] == "n1"
            assert len(result["triggered_impacts"]) == 1

    def test_ontology_rebac_check_granted(self):
        from opencrab.mcp.tools import dispatch_tool
        from opencrab.ontology.rebac import AccessDecision

        with patch("opencrab.mcp.tools._get_context") as mock_ctx:
            decision = AccessDecision(
                granted=True, reason="Direct graph relationship",
                subject_id="u1", permission="view", resource_id="doc1"
            )
            rebac = MagicMock()
            rebac.check.return_value = decision
            mock_ctx.return_value = {
                "builder": MagicMock(), "rebac": rebac,
                "impact": MagicMock(), "hybrid": MagicMock(), "documents": MagicMock(),
            }
            result = dispatch_tool("ontology_rebac_check", {
                "subject_id": "u1", "permission": "view", "resource_id": "doc1"
            })
            assert result["granted"] is True
            assert "Direct graph" in result["reason"]

    def test_ontology_lever_simulate(self):
        from opencrab.mcp.tools import dispatch_tool

        with patch("opencrab.mcp.tools._get_context") as mock_ctx:
            impact_engine = MagicMock()
            impact_engine.lever_simulate.return_value = {
                "lever_id": "lev1", "direction": "raises", "magnitude": 0.8,
                "predicted_outcome_changes": [], "confidence": 0.86,
            }
            mock_ctx.return_value = {
                "builder": MagicMock(), "rebac": MagicMock(),
                "impact": impact_engine, "hybrid": MagicMock(), "documents": MagicMock(),
            }
            result = dispatch_tool("ontology_lever_simulate", {
                "lever_id": "lev1", "direction": "raises", "magnitude": 0.8
            })
            assert result["lever_id"] == "lev1"
            assert result["confidence"] == 0.86

    def test_ontology_ingest_success(self):
        from opencrab.mcp.tools import dispatch_tool

        with patch("opencrab.mcp.tools._get_context") as mock_ctx:
            hybrid = MagicMock()
            hybrid.ingest.return_value = {
                "source_id": "src1",
                "stores": {"vectors": "ok (id=src1)"},
                "vector_id": "src1",
            }
            documents = MagicMock()
            documents.available = True
            documents.upsert_source.return_value = "doc-id-1"
            mock_ctx.return_value = {
                "builder": MagicMock(), "rebac": MagicMock(),
                "impact": MagicMock(), "hybrid": hybrid, "documents": documents,
            }
            result = dispatch_tool("ontology_ingest", {
                "text": "This is a test document about ontologies.",
                "source_id": "src1",
                "metadata": {"space": "evidence"},
            })
            assert result["source_id"] == "src1"
            assert "vectors" in result["stores"]
            assert result["text_length"] > 0

    def test_ontology_extract_works_without_external_llm(self):
        from opencrab.mcp.tools import dispatch_tool

        with patch("opencrab.mcp.tools._get_context") as mock_ctx:
            builder = MagicMock()
            builder.add_node.return_value = {"stores": {"graph": "ok"}}
            builder.add_edge.return_value = {"stores": {"graph": "ok"}}
            mock_ctx.return_value = {
                "builder": builder,
                "rebac": MagicMock(),
                "impact": MagicMock(),
                "hybrid": MagicMock(),
                "documents": MagicMock(),
            }

            result = dispatch_tool(
                "ontology_extract",
                {
                    "text": (
                        "Alice manages Project Atlas. "
                        "Cache TTL raises reliability for the analytics pipeline."
                    ),
                    "source_id": "incident-report.md",
                },
            )

            assert result["extractor_mode"] == "heuristic"
            assert result["extracted_nodes"] >= 2
            assert result["extracted_edges"] >= 1
            assert result["added_nodes"] >= 2
            assert result["added_edges"] >= 1

    def test_reset_runtime_state_rebuilds_context(self, monkeypatch, tmp_path):
        from opencrab.mcp.tools import _get_context, reset_runtime_state

        first_dir = tmp_path / "first"
        second_dir = tmp_path / "second"

        monkeypatch.setenv("LOCAL_DATA_DIR", str(first_dir))
        monkeypatch.setenv("CHROMA_COLLECTION", "reset-test-a")
        reset_runtime_state()
        first_ctx = _get_context()

        monkeypatch.setenv("LOCAL_DATA_DIR", str(second_dir))
        monkeypatch.setenv("CHROMA_COLLECTION", "reset-test-b")
        reset_runtime_state()
        second_ctx = _get_context()

        assert first_ctx is not second_ctx
        assert first_ctx["graph"] is not second_ctx["graph"]
        assert first_ctx["documents"] is not second_ctx["documents"]
        assert first_ctx["vectors"] is not second_ctx["vectors"]
        assert first_ctx["context_pipeline"] is not second_ctx["context_pipeline"]
        assert second_ctx["vectors"].location == str(second_dir / "chroma")

    def test_agent_context_pipeline_builds_bundle(self):
        from opencrab.ontology.context_pipeline import AgentContextPipeline, AgentContextRequest
        from opencrab.ontology.query import QueryResult

        hybrid = MagicMock()
        hybrid.query.return_value = [
            QueryResult(
                source="vector",
                node_id="n1",
                score=0.9,
                text="Vector fact",
                metadata={"source_id": "src-1", "space": "evidence"},
            ),
            QueryResult(
                source="graph",
                node_id="n2",
                score=0.5,
                text="Graph fact",
                metadata={"space": "concept"},
                graph_context={"anchor_id": "n1", "labels": ["Concept"]},
            ),
        ]
        pipeline = AgentContextPipeline(hybrid)

        bundle = pipeline.build_context(AgentContextRequest(question="cache ttl"))
        payload = bundle.to_dict()

        assert len(bundle.facts) == 2
        assert payload["facts"][0]["status"] == "confirmed"
        assert payload["facts"][1]["status"] == "inferred"
        assert payload["scope"]["graph_expansion_enabled"] is True
        assert payload["supporting_evidence"][0]["ref"] == "src-1"
        assert any(
            path["nodes"] == ["n1", "n2"] and path["relation"] == "graph_neighbor"
            for path in payload["provenance_paths"]
        )
        assert payload["inferred_links"][0]["relation"] == "neighbor_of"
        assert payload["raw_refs"][0]["ref_type"] == "node"

    def test_agent_context_pipeline_emits_missing_links_for_empty_scope(self):
        from opencrab.ontology.context_pipeline import AgentContextPipeline, AgentContextRequest

        hybrid = MagicMock()
        hybrid.query.return_value = []
        pipeline = AgentContextPipeline(hybrid)

        bundle = pipeline.build_context(
            AgentContextRequest(
                question="unknown topic",
                project="alpha",
                source_id_prefix="docs/",
            )
        )
        payload = bundle.to_dict()

        assert payload["facts"] == []
        assert payload["missing_links"][0]["kind"] == "no_match"
        assert payload["missing_links"][1]["kind"] == "scope_constrained_graph_expansion"
        assert payload["uncertainty"]["scope_filters_active"] is True

    def test_agent_context_pipeline_enriches_evidence_and_policy_hints(self):
        from opencrab.ontology.context_pipeline import AgentContextPipeline, AgentContextRequest
        from opencrab.ontology.query import QueryResult

        hybrid = MagicMock()
        hybrid.query.return_value = [
            QueryResult(
                source="vector",
                node_id="doc-1",
                score=0.92,
                text="Short summary",
                metadata={"source_id": "src-1", "space": "resource"},
            )
        ]
        documents = MagicMock()
        documents.available = True
        documents.get_source.return_value = {
            "text": "This is the longer supporting source text for doc-1.",
            "metadata": {"project": "alpha"},
        }
        documents.get_node_doc.return_value = {
            "properties": {"description": "Document node description"},
        }
        operational = MagicMock()
        operational.check_policy.return_value = True

        pipeline = AgentContextPipeline(hybrid, documents, operational)
        bundle = pipeline.build_context(
            AgentContextRequest(
                question="what can alice view",
                subject_id="alice",
                permission="view",
            )
        )
        payload = bundle.to_dict()

        assert payload["supporting_evidence"][0]["text_excerpt"].startswith(
            "This is the longer supporting source text"
        )
        assert payload["policies"][0]["subject_id"] == "alice"
        assert payload["policies"][0]["status"] == "granted"
        assert payload["provenance_paths"][0]["relation"] == "source_supports_fact"

    def test_agent_context_pipeline_degrades_when_enrichment_lookups_fail(self):
        from opencrab.ontology.context_pipeline import AgentContextPipeline, AgentContextRequest
        from opencrab.ontology.query import QueryResult

        hybrid = MagicMock()
        hybrid.query.return_value = [
            QueryResult(
                source="vector",
                node_id="doc-1",
                score=0.92,
                text="Short summary fallback",
                metadata={"source_id": "src-1", "space": "resource"},
            )
        ]
        documents = MagicMock()
        documents.available = True
        documents.get_source.side_effect = RuntimeError("doc store unavailable")
        operational = MagicMock()
        operational.check_policy.side_effect = RuntimeError("policy store unavailable")

        pipeline = AgentContextPipeline(hybrid, documents, operational)
        bundle = pipeline.build_context(
            AgentContextRequest(
                question="what can alice view",
                subject_id="alice",
                permission="view",
            )
        )
        payload = bundle.to_dict()

        assert payload["facts"][0]["node_id"] == "doc-1"
        assert payload["supporting_evidence"][0]["text_excerpt"] == "Short summary fallback"
        assert payload["policies"] == []
        assert {item["kind"] for item in payload["missing_links"]} == {
            "supporting_evidence_unavailable",
            "policy_hint_unavailable",
        }
        assert any(
            "Supporting source lookup failed for src-1" in note
            for note in payload["uncertainty"]["notes"]
        )
        assert any(
            "Policy hint lookup failed for doc-1" in note
            for note in payload["uncertainty"]["notes"]
        )


# ---------------------------------------------------------------------------
# MCP Server protocol tests
# ---------------------------------------------------------------------------


class TestMCPServer:
    @pytest.fixture
    def server(self):
        from opencrab.mcp.server import MCPServer

        with patch("opencrab.mcp.server.get_settings") as mock_cfg:
            mock_cfg.return_value = MagicMock(
                mcp_server_name="opencrab-test",
                mcp_server_version="0.0.1",
            )
            return MCPServer()

    def test_handle_parse_error(self, server):
        response = server._handle_raw("not json {{{")
        assert response["error"]["code"] == -32700  # PARSE_ERROR

    def test_handle_missing_method(self, server):
        request = json.dumps({"jsonrpc": "2.0", "id": 1, "params": {}})
        response = server._handle_raw(request)
        assert response["error"]["code"] == -32600  # INVALID_REQUEST

    def test_handle_unknown_method(self, server):
        request = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "unknown/method"})
        response = server._handle_raw(request)
        assert response["error"]["code"] == -32601  # METHOD_NOT_FOUND

    def test_handle_initialize(self, server):
        request = json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2025-11-25"},
        })
        response = server._handle_raw(request)
        assert response["id"] == 1
        result = response["result"]
        assert "protocolVersion" in result
        assert result["protocolVersion"] == "2025-11-25"
        assert "serverInfo" in result
        assert result["serverInfo"]["name"] == "opencrab-test"
        assert "capabilities" in result
        assert "tools" in result["capabilities"]
        assert "resources" in result["capabilities"]

    def test_handle_tools_list(self, server):
        request = json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        response = server._handle_raw(request)
        assert response["id"] == 2
        assert "tools" in response["result"]
        tools = response["result"]["tools"]
        assert len(tools) == 9

    def test_handle_initialized_notification_without_id_returns_none(self, server):
        request = json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"})
        response = server._handle_raw(request)
        assert response is None

    def test_handle_initialized_notification_with_null_id_returns_none(self, server):
        request = json.dumps({"jsonrpc": "2.0", "id": None, "method": "notifications/initialized"})
        response = server._handle_raw(request)
        assert response is None

    def test_handle_resources_list(self, server):
        request = json.dumps({"jsonrpc": "2.0", "id": 7, "method": "resources/list", "params": {}})
        response = server._handle_raw(request)
        assert response["id"] == 7
        assert response["result"]["resources"] == []

    def test_handle_resource_templates_list(self, server):
        request = json.dumps({
            "jsonrpc": "2.0",
            "id": 8,
            "method": "resources/templates/list",
            "params": {},
        })
        response = server._handle_raw(request)
        assert response["id"] == 8
        assert response["result"]["resourceTemplates"] == []

    def test_handle_batch_request(self, server):
        batch = json.dumps(
            [
                {"jsonrpc": "2.0", "method": "notifications/initialized"},
                {"jsonrpc": "2.0", "id": 9, "method": "resources/list", "params": {}},
                {"jsonrpc": "2.0", "id": 10, "method": "resources/templates/list", "params": {}},
            ]
        )
        response = server._handle_raw(batch)
        assert isinstance(response, list)
        assert len(response) == 2
        assert response[0]["id"] == 9
        assert response[0]["result"]["resources"] == []
        assert response[1]["id"] == 10
        assert response[1]["result"]["resourceTemplates"] == []

    def test_handle_tools_call_manifest(self, server):
        request = json.dumps({
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "ontology_manifest",
                "arguments": {},
            },
        })
        response = server._handle_raw(request)
        assert response["id"] == 3
        assert "content" in response["result"]
        content = response["result"]["content"]
        assert len(content) == 1
        assert content[0]["type"] == "text"

        # The text should be valid JSON containing the grammar
        grammar = json.loads(content[0]["text"])
        assert "spaces" in grammar
        assert "meta_edges" in grammar

    def test_handle_tools_call_missing_name(self, server):
        request = json.dumps({
            "jsonrpc": "2.0", "id": 4,
            "method": "tools/call",
            "params": {"arguments": {}},
        })
        response = server._handle_raw(request)
        # Missing name → invalid params or internal error
        assert "error" in response

    def test_handle_tools_call_unknown_tool(self, server):
        request = json.dumps({
            "jsonrpc": "2.0", "id": 5,
            "method": "tools/call",
            "params": {"name": "unknown_tool", "arguments": {}},
        })
        response = server._handle_raw(request)
        # Should return method not found
        assert "error" in response

    def test_handle_ping(self, server):
        request = json.dumps({"jsonrpc": "2.0", "id": 99, "method": "ping"})
        response = server._handle_raw(request)
        assert response["result"]["status"] == "ok"

    def test_empty_line_returns_none(self, server):
        result = server._handle_raw("")
        assert result is None

    def test_response_id_matches_request(self, server):
        for req_id in [1, 42, "abc", None]:
            request = json.dumps({"jsonrpc": "2.0", "id": req_id, "method": "unknown"})
            response = server._handle_raw(request)
            assert response["id"] == req_id


# ---------------------------------------------------------------------------
# OntologyBuilder unit tests (local-first runtime)
# ---------------------------------------------------------------------------


class TestOntologyBuilder:
    @pytest.fixture
    def builder(self, tmp_path):
        from opencrab.ontology.builder import OntologyBuilder
        from opencrab.stores.duckdb_store import DuckDBStore
        from opencrab.stores.ladybug_store import LadybugStore

        graph = LadybugStore(str(tmp_path / "graph.lbug"))
        store = DuckDBStore(str(tmp_path / "opencrab.db"))
        return OntologyBuilder(graph, store, store)

    def test_add_node_valid(self, builder):
        result = builder.add_node("subject", "User", "u1", {"name": "Alice"})
        assert result["node_id"] == "u1"
        assert result["space"] == "subject"
        assert result["node_type"] == "User"
        assert "stores" in result
        assert result["stores"]["graph"] == "ok"
        assert result["stores"]["documents"].startswith("ok")
        assert result["stores"]["registry"] == "ok"

    def test_add_node_graph_failure_skips_registry_and_logs_failure(self, tmp_path):
        from opencrab.ontology.builder import OntologyBuilder
        from opencrab.stores.duckdb_store import DuckDBStore

        graph = MagicMock()
        graph.available = True
        graph.upsert_node.side_effect = RuntimeError("graph offline")
        store = DuckDBStore(str(tmp_path / "opencrab.db"))
        builder = OntologyBuilder(graph, store, store)

        result = builder.add_node("subject", "User", "u1", {"name": "Alice"})

        assert result["stores"]["graph"] == "error: graph offline"
        assert result["stores"]["registry"] == "skipped (graph node not persisted)"
        assert result["stores"]["documents"] == "failure_audited"
        assert store.get_node_doc("subject", "u1") is None
        assert store.table_counts()["ontology_nodes"] == 0

        events = store.get_audit_log()
        assert len(events) == 1
        assert events[0]["event_type"] == "node_upsert_failed"
        assert events[0]["details"]["graph_status"] == "error: graph offline"

    def test_add_node_invalid_space(self, builder):
        with pytest.raises(ValueError, match="badspace"):
            builder.add_node("badspace", "User", "u1")

    def test_add_node_invalid_type(self, builder):
        with pytest.raises(ValueError, match="Document"):
            builder.add_node("subject", "Document", "u1")

    def test_add_edge_valid(self, builder):
        builder.add_node("subject", "User", "u1")
        builder.add_node("resource", "Project", "p1")
        result = builder.add_edge("subject", "u1", "owns", "resource", "p1")
        assert result["relation"] == "owns"
        assert result["stores"]["registry"] == "ok"

    def test_add_edge_missing_nodes_skips_registry_and_logs_failure(self, builder):
        result = builder.add_edge("subject", "u1", "owns", "resource", "p1")

        assert result["stores"]["graph"] == "no match"
        assert result["stores"]["registry"] == "skipped (graph edge not persisted)"
        assert result["stores"]["documents"] == "failure_audited"

        counts = builder._sql.table_counts()
        assert counts["ontology_edges"] == 0

        events = builder._mongo.get_audit_log()
        assert len(events) == 1
        assert events[0]["event_type"] == "edge_upsert_failed"
        assert events[0]["details"]["graph_status"] == "no match"

    def test_add_edge_invalid_relation(self, builder):
        with pytest.raises(ValueError):
            builder.add_edge("subject", "u1", "mentions", "resource", "p1")

    def test_add_edge_invalid_space_pair(self, builder):
        with pytest.raises(ValueError):
            builder.add_edge("outcome", "o1", "owns", "subject", "u1")


# ---------------------------------------------------------------------------
# ReBACEngine unit tests (local-first runtime)
# ---------------------------------------------------------------------------


class TestReBACEngine:
    @pytest.fixture
    def engine(self, tmp_path):
        from opencrab.ontology.rebac import ReBACEngine
        from opencrab.stores.duckdb_store import DuckDBStore
        from opencrab.stores.ladybug_store import LadybugStore

        graph = LadybugStore(str(tmp_path / "graph.lbug"))
        sql = DuckDBStore(str(tmp_path / "opencrab.db"))
        return ReBACEngine(graph, sql)

    def test_check_denied_when_no_policy_no_graph(self, engine):
        decision = engine.check("u1", "view", "doc1")
        assert decision.granted is False
        assert "Default deny" in decision.reason

    def test_explicit_grant(self, engine):
        engine.grant("u1", "view", "doc1")
        decision = engine.check("u1", "view", "doc1")
        assert decision.granted is True

    def test_explicit_deny(self, engine):
        engine.grant("u1", "edit", "doc2")
        engine.deny("u1", "edit", "doc2")
        decision = engine.check("u1", "edit", "doc2")
        assert decision.granted is False
        assert "DENY" in decision.reason

    def test_invalid_permission_returns_deny(self, engine):
        decision = engine.check("u1", "delete", "doc1")
        assert decision.granted is False
        # The reason should contain either "Invalid permission" or "Unknown permission"
        assert "permission" in decision.reason.lower()

    def test_list_policies(self, engine):
        engine.grant("u2", "view", "r1")
        engine.grant("u2", "edit", "r2")
        policies = engine.list_subject_policies("u2")
        assert len(policies) == 2


# ---------------------------------------------------------------------------
# ImpactEngine unit tests (local-first runtime)
# ---------------------------------------------------------------------------


class TestImpactEngine:
    @pytest.fixture
    def engine(self, tmp_path):
        from opencrab.ontology.impact import ImpactEngine
        from opencrab.stores.duckdb_store import DuckDBStore
        from opencrab.stores.ladybug_store import LadybugStore

        graph = LadybugStore(str(tmp_path / "graph.lbug"))
        sql = DuckDBStore(str(tmp_path / "opencrab.db"))
        return ImpactEngine(graph, sql)

    def test_analyse_returns_impact_result(self, engine):
        from opencrab.ontology.impact import ImpactResult

        result = engine.analyse("n1", "update")
        assert isinstance(result, ImpactResult)
        assert result.node_id == "n1"
        assert result.change_type == "update"
        assert len(result.triggered) > 0

    def test_analyse_always_triggers_i1(self, engine):
        result = engine.analyse("n2", "create")
        triggered_ids = {t["id"] for t in result.triggered}
        assert "I1" in triggered_ids

    def test_analyse_delete_triggers_multiple(self, engine):
        result = engine.analyse("n3", "delete")
        triggered_ids = {t["id"] for t in result.triggered}
        # Delete should trigger data, relation, and logic impacts
        assert len(triggered_ids) >= 3

    def test_analyse_persists_to_sql(self, engine):
        engine.analyse("n4", "update")
        records = engine._sql.get_impacts("n4")
        assert len(records) >= 1

    def test_lever_simulate_invalid_direction(self, engine):
        with pytest.raises(ValueError, match="invalid_dir"):
            engine.lever_simulate("lev1", "invalid_dir", 0.5)

    def test_lever_simulate_returns_dict(self, engine):
        result = engine.lever_simulate("lev1", "raises", 0.7)
        assert result["lever_id"] == "lev1"
        assert result["direction"] == "raises"
        assert result["magnitude"] == 0.7
        assert "confidence" in result
        assert result["confidence"] > 0
