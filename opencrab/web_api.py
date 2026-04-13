"""Packaged local web/API sidecar entrypoint for little-crab."""

from __future__ import annotations

from collections import Counter
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from opencrab.config import get_settings
from opencrab.ontology.context_pipeline import AgentContextRequest
from opencrab.stores.factory import make_runtime_services, make_runtime_stores


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1)
    spaces: list[str] | None = None
    limit: int = Field(default=10, ge=1, le=50)
    project: str | None = None
    source_id_prefix: str | None = None


app = FastAPI(title="little-crab local ui api", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _stores() -> Any:
    return make_runtime_stores(get_settings())


def _services() -> Any:
    return make_runtime_services(get_settings())


@app.get("/api/status")
def status() -> dict[str, Any]:
    stores = _stores()
    return {
        "ok": True,
        "mode": "local",
        "stores": {
            "graph": bool(stores.graph.available),
            "documents": bool(stores.documents.available),
            "registry": bool(stores.sql.available),
            "vectors": bool(stores.vector.available),
        },
    }


@app.get("/api/nodes")
def nodes() -> dict[str, Any]:
    stores = _stores()
    node_docs = stores.documents.list_nodes()
    edge_rows = stores.sql.list_edges(limit=5000)
    degree: Counter[str] = Counter()
    for edge in edge_rows:
        degree[str(edge["from_id"])] += 1
        degree[str(edge["to_id"])] += 1

    payload = [
        {
            "id": str(node["node_id"]),
            "space": str(node["space"]),
            "node_type": str(node["node_type"]),
            "properties": dict(node.get("properties") or {}),
            "degree": degree.get(str(node["node_id"]), 0),
        }
        for node in node_docs
    ]
    return {"nodes": payload}


@app.get("/api/edges")
def edges() -> dict[str, Any]:
    stores = _stores()
    payload = [
        {
            "from_id": str(edge["from_id"]),
            "to_id": str(edge["to_id"]),
            "relation": str(edge["relation"]),
            "from_space": str(edge["from_space"]),
            "to_space": str(edge["to_space"]),
        }
        for edge in stores.sql.list_edges(limit=5000)
    ]
    return {"edges": payload}


@app.post("/api/query")
def query(request: QueryRequest) -> dict[str, Any]:
    services = _services()
    bundle = services.context_pipeline.build_context(
        AgentContextRequest(
            question=request.question,
            spaces=request.spaces,
            limit=request.limit,
            project=request.project,
            source_id_prefix=request.source_id_prefix,
        )
    )
    return {
        "question": request.question,
        "results": bundle.legacy_results(),
        "context": bundle.to_dict(),
        "total": len(bundle.facts),
    }


@app.get("/api/node/{node_id}")
def node_detail(node_id: str) -> dict[str, Any]:
    stores = _stores()
    for node in stores.documents.list_nodes():
        if str(node["node_id"]) == node_id:
            return {
                "id": str(node["node_id"]),
                "space": str(node["space"]),
                "node_type": str(node["node_type"]),
                "properties": dict(node.get("properties") or {}),
            }
    raise HTTPException(status_code=404, detail="node not found")


def main() -> None:
    uvicorn.run(app, host="127.0.0.1", port=8000)
