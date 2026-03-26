"""
Run repeatable local MCP dogfood scenarios against little-crab.

Usage:
    py -3.12 scripts/dogfood_mcp.py
    py -3.12 scripts/dogfood_mcp.py --data-dir ./.dogfood-data --keep-data-dir
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


class MCPDogfoodError(RuntimeError):
    """Raised when a dogfood scenario fails."""


class MCPClient:
    """Small JSON-RPC client for the local stdio MCP server."""

    def __init__(self, data_dir: Path) -> None:
        env = os.environ.copy()
        env["LOCAL_DATA_DIR"] = str(data_dir)
        env.setdefault("STORAGE_MODE", "local")
        env.setdefault("CHROMA_COLLECTION", "little_crab_vectors")
        env.setdefault("MCP_SERVER_NAME", "little-crab")
        env.setdefault("MCP_SERVER_VERSION", "0.1.0")
        env.setdefault("LOG_LEVEL", "WARNING")

        self._proc = subprocess.Popen(
            [sys.executable, "-m", "opencrab.cli", "serve"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            cwd=str(Path(__file__).resolve().parents[1]),
            env=env,
        )
        self._next_id = 1

    def close(self) -> None:
        if self._proc.stdin:
            self._proc.stdin.close()
        try:
            self._proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._proc.kill()
                self._proc.wait(timeout=5)

    def request(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        if self._proc.stdin is None or self._proc.stdout is None:
            raise MCPDogfoodError("MCP process pipes are unavailable.")

        req_id = self._next_id
        self._next_id += 1
        payload = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params or {},
        }
        self._proc.stdin.write(json.dumps(payload) + "\n")
        self._proc.stdin.flush()

        raw = self._proc.stdout.readline()
        if not raw:
            stderr = ""
            if self._proc.stderr is not None:
                stderr = self._proc.stderr.read()
            raise MCPDogfoodError(f"No response from MCP server. stderr={stderr!r}")

        response = json.loads(raw)
        if "error" in response:
            raise MCPDogfoodError(f"MCP error for {method}: {response['error']}")
        return response["result"]

    def tool(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        result = self.request(
            "tools/call",
            {"name": name, "arguments": arguments or {}},
        )
        content = result.get("content") or []
        if not content:
            raise MCPDogfoodError(f"Tool {name} returned no content.")
        text = content[0].get("text", "")
        return json.loads(text) if text else {}


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise MCPDogfoodError(message)


def scenario_manifest_and_writes(client: MCPClient) -> None:
    grammar = client.tool("ontology_manifest")
    _assert("spaces" in grammar and "meta_edges" in grammar, "Manifest missing grammar keys.")

    node_a = client.tool(
        "ontology_add_node",
        {
            "space": "subject",
            "node_type": "User",
            "node_id": "dogfood-user",
            "properties": {"name": "Dogfood User"},
        },
    )
    _assert(node_a.get("node_id") == "dogfood-user", "Failed to add subject node.")

    node_b = client.tool(
        "ontology_add_node",
        {
            "space": "resource",
            "node_type": "Document",
            "node_id": "dogfood-doc",
            "properties": {"name": "Dogfood Document"},
        },
    )
    _assert(node_b.get("node_id") == "dogfood-doc", "Failed to add resource node.")

    edge = client.tool(
        "ontology_add_edge",
        {
            "from_space": "subject",
            "from_id": "dogfood-user",
            "relation": "owns",
            "to_space": "resource",
            "to_id": "dogfood-doc",
        },
    )
    _assert(edge.get("relation") == "owns", "Failed to add grammar-validated edge.")


def scenario_ingest_extract_query(client: MCPClient) -> None:
    ingested = client.tool(
        "ontology_ingest",
        {
            "text": (
                "Cache TTL tuning improved reliability and reduced stale reads for the analytics "
                "platform during peak traffic."
            ),
            "source_id": "dogfood-src-1",
            "metadata": {"space": "lever", "node_id": "lever-cache-ttl"},
        },
    )
    _assert("vectors" in ingested.get("stores", {}), "Ingest did not write to vector store.")

    extracted = client.tool(
        "ontology_extract",
        {
            "text": (
                "Cache TTL raises reliability for the analytics platform. "
                "Alice reviewed the resulting incident report."
            ),
            "source_id": "dogfood-extract-1",
        },
    )
    _assert(extracted.get("added_nodes", 0) >= 2, "Extraction did not add expected nodes.")

    queried = client.tool(
        "ontology_query",
        {"question": "cache ttl reliability", "limit": 5},
    )
    _assert(queried.get("total", 0) >= 1, "Query returned no results after ingest/extract.")


def scenario_rebac_impact_and_simulation(client: MCPClient) -> None:
    client.tool(
        "ontology_add_node",
        {
            "space": "subject",
            "node_type": "User",
            "node_id": "reviewer-user",
            "properties": {"name": "Reviewer User"},
        },
    )
    client.tool(
        "ontology_add_node",
        {
            "space": "resource",
            "node_type": "Dataset",
            "node_id": "events-dataset",
            "properties": {"name": "Events Dataset"},
        },
    )
    client.tool(
        "ontology_add_edge",
        {
            "from_space": "subject",
            "from_id": "reviewer-user",
            "relation": "can_view",
            "to_space": "resource",
            "to_id": "events-dataset",
        },
    )

    decision = client.tool(
        "ontology_rebac_check",
        {
            "subject_id": "reviewer-user",
            "permission": "view",
            "resource_id": "events-dataset",
        },
    )
    _assert(decision.get("granted") is True, "ReBAC check did not grant expected access.")

    client.tool(
        "ontology_add_node",
        {
            "space": "lever",
            "node_type": "Lever",
            "node_id": "cache-ttl-lever",
            "properties": {"name": "Cache TTL"},
        },
    )
    client.tool(
        "ontology_add_node",
        {
            "space": "outcome",
            "node_type": "Outcome",
            "node_id": "system-reliability",
            "properties": {"name": "System Reliability"},
        },
    )
    client.tool(
        "ontology_add_edge",
        {
            "from_space": "lever",
            "from_id": "cache-ttl-lever",
            "relation": "raises",
            "to_space": "outcome",
            "to_id": "system-reliability",
        },
    )

    impact = client.tool(
        "ontology_impact",
        {"node_id": "cache-ttl-lever", "change_type": "update"},
    )
    _assert(
        len(impact.get("triggered_impacts", [])) >= 1,
        "Impact analysis did not return triggered categories.",
    )

    simulation = client.tool(
        "ontology_lever_simulate",
        {"lever_id": "cache-ttl-lever", "direction": "raises", "magnitude": 0.7},
    )
    _assert(
        len(simulation.get("predicted_outcome_changes", [])) >= 1,
        "Lever simulation did not return predicted outcome changes.",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run local MCP dogfood scenarios.")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=None,
        help="Optional LOCAL_DATA_DIR to use. Defaults to a temporary directory.",
    )
    parser.add_argument(
        "--keep-data-dir",
        action="store_true",
        help="Preserve the data directory after the run.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    cleanup_dir = False
    if args.data_dir is None:
        data_dir = Path(tempfile.mkdtemp(prefix="little-crab-dogfood-"))
        cleanup_dir = not args.keep_data_dir
    else:
        data_dir = args.data_dir.resolve()
        data_dir.mkdir(parents=True, exist_ok=True)
        cleanup_dir = False

    client = MCPClient(data_dir=data_dir)
    try:
        init_result = client.request("initialize", {})
        tools = client.request("tools/list", {})
        _assert(init_result.get("serverInfo", {}).get("name"), "Initialize missing server info.")
        _assert(len(tools.get("tools", [])) >= 9, "tools/list returned too few tools.")

        scenario_manifest_and_writes(client)
        scenario_ingest_extract_query(client)
        scenario_rebac_impact_and_simulation(client)
    except MCPDogfoodError as exc:
        print(f"FAIL: {exc}")
        print(f"LOCAL_DATA_DIR={data_dir}")
        return 1
    finally:
        client.close()

    print("PASS: MCP dogfood scenarios completed.")
    print(f"LOCAL_DATA_DIR={data_dir}")

    if cleanup_dir:
        shutil.rmtree(data_dir, ignore_errors=True)
        print("Cleanup: temporary data directory removed.")
    elif not args.keep_data_dir:
        print("Cleanup: preserved user-supplied data directory.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
