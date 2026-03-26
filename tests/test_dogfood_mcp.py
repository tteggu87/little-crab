"""Tests for MCP dogfood evidence capture helpers."""

from __future__ import annotations

import json

from scripts.dogfood_mcp import SessionRecorder


def test_session_recorder_writes_sanitized_evidence(tmp_path) -> None:
    data_dir = tmp_path / "runtime-data"
    data_dir.mkdir()
    out_dir = tmp_path / "evidence"

    recorder = SessionRecorder(data_dir)
    recorder.record(
        "initialize",
        {"cwd": str(data_dir)},
        {"serverInfo": {"name": "little-crab"}, "path": str(data_dir / "graph.lbug")},
    )
    recorder.set_scenario("scenario_1_manifest_node_edge")
    recorder.record(
        "tools/call",
        {"name": "ontology_manifest", "arguments": {"source": str(data_dir)}},
        {"content": [{"type": "text", "text": str(data_dir / "opencrab.db")}]},
    )

    recorder.write(
        out_dir,
        {
            "bootstrap": {"server_name": "little-crab", "tool_count": 9},
            "scenario_1_manifest_node_edge": {"created_nodes": ["n1", "n2"]},
        },
        status="pass",
    )

    transcript = (out_dir / "transcript.json").read_text(encoding="utf-8")
    assert str(data_dir) not in transcript
    assert "<LOCAL_DATA_DIR>" in transcript

    summary = json.loads((out_dir / "session_summary.json").read_text(encoding="utf-8"))
    assert summary["status"] == "pass"
    assert summary["scenario_count"] == 2

    scenario_payload = json.loads(
        (out_dir / "scenario-1-manifest-node-edge.json").read_text(encoding="utf-8")
    )
    assert scenario_payload["scenario"] == "scenario_1_manifest_node_edge"
