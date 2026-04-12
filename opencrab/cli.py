"""
little-crab CLI — Click command interface.

Commands:
  init      Create .env from template
  serve     Start the MCP server (stdio)
  status    Check all store connections
  doctor    Run a richer runtime doctor report
  ingest    Ingest files from a path
  query     Run a hybrid query
  manifest  Print the MetaOntology grammar
  stage-*   Queue node or edge writes for later publish
"""

from __future__ import annotations

import json
import logging
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


# ---------------------------------------------------------------------------
# Main group
# ---------------------------------------------------------------------------


@click.group()
@click.version_option(package_name="little-crab")
def main() -> None:
    """little-crab — local-first MetaOntology MCP runtime."""


# ---------------------------------------------------------------------------
# init
# ---------------------------------------------------------------------------


@main.command()
@click.option(
    "--force", is_flag=True, default=False, help="Overwrite existing .env file."
)
def init(force: bool) -> None:
    """Create a .env file from .env.example and show startup instructions."""
    here = Path.cwd()
    src = here / ".env.example"
    dst = here / ".env"

    # Search for .env.example up from cwd (handles running from subdirs)
    if not src.exists():
        pkg_dir = Path(__file__).parent.parent
        src = pkg_dir / ".env.example"

    if dst.exists() and not force:
        console.print(
            "[yellow].env already exists. Use --force to overwrite.[/yellow]"
        )
    else:
        if src.exists():
            shutil.copy(src, dst)
            console.print(f"[green]Created {dst}[/green]")
        else:
            _write_default_env(dst)
            console.print(f"[green]Created default {dst}[/green]")

    console.print(
        Panel(
            "[bold]Next steps:[/bold]\n\n"
            "1. Edit [cyan].env[/cyan] if you want a custom data path.\n"
            "2. Verify the embedded runtime:\n"
            "   [cyan]littlecrab status[/cyan]\n"
            "3. Seed the embedded stores:\n"
            "   [cyan]python scripts/seed_ontology.py[/cyan]\n"
            "4. Add to Claude Code MCP config:\n"
            "   [cyan]claude mcp add little-crab -- littlecrab serve[/cyan]\n\n"
            "[dim]Compatibility aliases remain available: ltcrab, little-crab, opencrab (deprecated)[/dim]",
            title="little-crab Setup",
            border_style="green",
        )
    )


def _write_default_env(path: Path) -> None:
    content = """\
STORAGE_MODE=local
LOCAL_DATA_DIR=./opencrab_data
CHROMA_COLLECTION=little_crab_vectors
CHROMA_EMBEDDING_PROVIDER=onnx
OLLAMA_URL=http://localhost:11434
OLLAMA_EMBEDDING_MODEL=qwen3-embedding:4b
OLLAMA_TIMEOUT=60
MCP_SERVER_NAME=little-crab
MCP_SERVER_VERSION=0.1.0
LOG_LEVEL=INFO
"""
    path.write_text(content)


# ---------------------------------------------------------------------------
# serve
# ---------------------------------------------------------------------------


@main.command()
def serve() -> None:
    """Start the little-crab MCP server on stdio."""
    # Suppress all non-error logging to keep stdio clean
    logging.basicConfig(level=logging.ERROR, stream=sys.stderr)
    from opencrab.mcp.server import MCPServer

    server = MCPServer()
    server.run()


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------


@main.command()
def status() -> None:
    """Check connectivity to the embedded local stores."""
    from opencrab.config import get_settings
    from opencrab.stores.factory import (
        make_graph_store,
        make_sql_store,
        make_vector_store,
    )

    cfg = get_settings()
    mode_label = "[bold cyan]LOCAL MODE[/bold cyan]"
    storage_loc = cfg.local_data_dir
    console.print(f"\n{mode_label} - storage at: {storage_loc}\n")

    graph = make_graph_store(cfg)
    vector = make_vector_store(cfg)
    sql = make_sql_store(cfg)

    store_rows: list[tuple[str, str, Any]] = [
        ("Graph (LadybugDB)", cfg.local_data_dir + "/graph.lbug", graph),
        (
            "Vector (ChromaDB Embedded)",
            getattr(vector, "location", cfg.local_data_dir + "/chroma"),
            vector,
        ),
        ("Operational Store (DuckDB)", cfg.local_data_dir + "/opencrab.db", sql),
    ]

    table = Table(title="little-crab Store Status", show_header=True, header_style="bold cyan")
    table.add_column("Store", style="bold")
    table.add_column("Path / URL")
    table.add_column("Status")

    for name, url, store in store_rows:
        if store.available:
            try:
                ok = store.ping()
                status_text = "[green]OK[/green]" if ok else "[yellow]CONNECTED (ping failed)[/yellow]"
            except Exception:
                status_text = "[yellow]CONNECTED[/yellow]"
        else:
            status_text = "[red]UNAVAILABLE[/red]"
        table.add_row(name, url, status_text)

    console.print(table)


# ---------------------------------------------------------------------------
# doctor
# ---------------------------------------------------------------------------


@main.command()
@click.option("--json-output", is_flag=True, default=False, help="Output raw JSON.")
def doctor(json_output: bool) -> None:
    """Run a richer runtime doctor report, including an isolated closure smoke."""
    from opencrab.config import get_settings

    cfg = get_settings()
    report = _build_doctor_report(cfg)

    if json_output:
        click.echo(json.dumps(report, indent=2, default=str))
        return

    console.print(
        Panel(
            f"[bold]little-crab Doctor[/bold]\n\n"
            f"Runtime path: [cyan]{report['local_data_dir']}[/cyan]\n"
            "Smoke mode: [cyan]isolated temp runtime[/cyan]",
            border_style="blue",
        )
    )

    store_table = Table(title="Runtime Health", show_header=True, header_style="bold blue")
    store_table.add_column("Store", style="bold")
    store_table.add_column("Status")
    store_table.add_column("Notes")
    for row in report["stores"]:
        status_text = "[green]OK[/green]" if row["available"] and row["ping"] else "[red]ISSUE[/red]"
        notes = ", ".join(row["notes"]) if row["notes"] else "-"
        store_table.add_row(row["label"], status_text, notes)
    console.print(store_table)

    count_table = Table(title="Current Counts", show_header=True, header_style="bold blue")
    count_table.add_column("Metric", style="bold")
    count_table.add_column("Value")
    for key, value in report["counts"].items():
        count_table.add_row(key, str(value))
    console.print(count_table)

    smoke = report["closure_smoke"]
    smoke_status = "[green]PASSED[/green]" if smoke["passed"] else "[red]FAILED[/red]"
    console.print(
        Panel(
            f"Status: {smoke_status}\n"
            f"Node write: {smoke['node_write_status']}\n"
            f"Vector ingest: {smoke['vector_ingest_status']}\n"
            f"Query match: {smoke['query_match']}\n"
            f"Supporting evidence count: {smoke['supporting_evidence_count']}",
            title="Closure Smoke",
            border_style="green" if smoke["passed"] else "red",
        )
    )

    if report["degraded_reasons"]:
        console.print("[bold yellow]Degraded Reasons[/bold yellow]")
        for reason in report["degraded_reasons"]:
            console.print(f"- {reason}")


# ---------------------------------------------------------------------------
# ingest
# ---------------------------------------------------------------------------


@main.command()
@click.argument("path", type=click.Path(exists=True))
@click.option("--recursive", "-r", is_flag=True, default=False)
@click.option("--extension", "-e", default=".txt,.md,.py", show_default=True)
def ingest(path: str, recursive: bool, extension: str) -> None:
    """Ingest files from PATH into the ontology vector store."""
    from opencrab.config import get_settings
    from opencrab.stores.factory import (
        make_doc_store,
        make_vector_store,
    )

    cfg = get_settings()
    vector = make_vector_store(cfg)
    docs = make_doc_store(cfg)

    extensions = [e.strip() for e in extension.split(",") if e.strip()]
    root = Path(path)

    if root.is_file():
        files = [root]
    else:
        files = list(root.rglob("*")) if recursive else list(root.iterdir())

    files = [f for f in files if f.is_file() and f.suffix in extensions]

    if not files:
        console.print(f"[yellow]No files with extensions {extensions} found in {path}[/yellow]")
        return

    console.print(f"[cyan]Ingesting {len(files)} file(s)...[/cyan]")

    records: list[dict[str, Any]] = []
    for file in files:
        try:
            text = file.read_text(encoding="utf-8", errors="ignore")
            if not text.strip():
                continue
            records.append(
                {
                    "file": file,
                    "text": text,
                    "source_id": str(file.resolve()),
                    "metadata": {"source_path": str(file), "extension": file.suffix},
                }
            )
        except Exception as exc:
            console.print(f"  [red]FAIL[/red] {file.name}: {exc}")

    ok_count = 0
    if records:
        vector_ids = [record["source_id"] for record in records]
        vector_texts = [record["text"] for record in records]
        vector_metadatas = [
            {**record["metadata"], "source_id": record["source_id"]}
            for record in records
        ]
        try:
            vector.upsert_texts(
                texts=vector_texts,
                metadatas=vector_metadatas,
                ids=vector_ids,
            )
            if docs.available:
                bulk_upsert = getattr(docs, "upsert_sources", None)
                if callable(bulk_upsert):
                    bulk_upsert(
                        [
                            {
                                "source_id": source_id,
                                "text": text,
                                "metadata": record["metadata"],
                            }
                            for record, source_id, text in zip(
                                records,
                                vector_ids,
                                vector_texts,
                                strict=True,
                            )
                        ]
                    )
                else:
                    for record in records:
                        docs.upsert_source(
                            record["source_id"],
                            record["text"],
                            record["metadata"],
                        )

            ok_count = len(records)
            for record in records:
                console.print(
                    f"  [green]OK[/green] {record['file'].name} ({len(record['text'])} chars)"
                )
        except Exception:
            for record in records:
                try:
                    source_id = record["source_id"]
                    text = record["text"]
                    vector.upsert_texts(
                        texts=[text],
                        metadatas=[{**record["metadata"], "source_id": source_id}],
                        ids=[source_id],
                    )
                    if docs.available:
                        docs.upsert_source(
                            source_id,
                            text,
                            record["metadata"],
                        )
                    ok_count += 1
                    console.print(
                        f"  [green]OK[/green] {record['file'].name} ({len(record['text'])} chars)"
                    )
                except Exception as exc:
                    console.print(f"  [red]FAIL[/red] {record['file'].name}: {exc}")

    console.print(f"\n[bold green]Ingested {ok_count}/{len(files)} files.[/bold green]")


# ---------------------------------------------------------------------------
# query
# ---------------------------------------------------------------------------


@main.command()
@click.argument("question")
@click.option("--spaces", "-s", default=None, help="Comma-separated space IDs to filter.")
@click.option("--limit", "-n", default=10, show_default=True)
@click.option("--project", default=None, help="Optional project metadata filter.")
@click.option("--source-id-prefix", default=None, help="Optional source_id prefix filter.")
@click.option("--json-output", is_flag=True, default=False, help="Output raw JSON.")
def query(
    question: str,
    spaces: str | None,
    limit: int,
    project: str | None,
    source_id_prefix: str | None,
    json_output: bool,
) -> None:
    """Run a trustability-oriented hybrid query and print results."""
    from opencrab.config import get_settings
    from opencrab.ontology.context_pipeline import AgentContextPipeline, AgentContextRequest
    from opencrab.ontology.query import HybridQuery
    from opencrab.stores.factory import (
        make_doc_store,
        make_graph_store,
        make_sql_store,
        make_vector_store,
    )

    cfg = get_settings()
    chroma = make_vector_store(cfg)
    graph = make_graph_store(cfg)
    docs = make_doc_store(cfg)
    sql = make_sql_store(cfg)
    pipeline = AgentContextPipeline(HybridQuery(chroma, graph), docs, sql)

    space_filter = [s.strip() for s in spaces.split(",")] if spaces else None

    bundle = pipeline.build_context(
        AgentContextRequest(
            question=question,
            spaces=space_filter,
            limit=limit,
            project=project,
            source_id_prefix=source_id_prefix,
        )
    )
    payload = _bundle_payload(
        question=question,
        bundle=bundle,
        spaces=space_filter,
        project=project,
        source_id_prefix=source_id_prefix,
    )

    if json_output:
        click.echo(json.dumps(payload, indent=2, default=str))
        return

    if not bundle.facts:
        console.print("[yellow]No results found.[/yellow]")
        for gap in bundle.missing_links[:5]:
            console.print(f"[dim]- {gap.kind}: {gap.description}[/dim]")
        return

    console.print(f"\n[bold]Query:[/bold] {question}")
    if project:
        console.print(f"[dim]Project filter: {project}[/dim]")
    if source_id_prefix:
        console.print(f"[dim]Source prefix filter: {source_id_prefix}[/dim]")
    console.print(
        "[dim]"
        f"Found {payload['total']} fact(s) | "
        f"confirmed={payload['confirmed_facts']} | "
        f"inferred={payload['inferred_facts']} | "
        f"evidence={payload['supporting_evidence_count']} | "
        f"paths={payload['provenance_path_count']}"
        "[/dim]\n"
    )

    for i, fact in enumerate(bundle.facts, 1):
        evidence = _find_supporting_evidence(bundle, fact)
        paths = _find_provenance_paths(bundle, fact)
        console.print(
            f"[bold cyan]{i}.[/bold cyan] "
            f"[{fact.source}] "
            f"status={fact.status} "
            f"node={fact.node_id or '?'} "
            f"score={fact.score:.3f}"
        )
        if fact.text:
            preview = fact.text[:200].replace("\n", " ")
            console.print(f"   [dim]{preview}...[/dim]")
        if evidence is not None:
            console.print(f"   evidence: {evidence.ref} ({evidence.ref_type})")
        if paths:
            console.print(
                "   trace: "
                + " | ".join(f"{path.relation}:{' -> '.join(path.nodes)}" for path in paths[:2])
            )
        console.print()

    if bundle.missing_links:
        console.print("[bold yellow]Known Gaps[/bold yellow]")
        for gap in bundle.missing_links[:5]:
            console.print(f"- {gap.kind}: {gap.description}")

    if bundle.uncertainty.get("notes"):
        console.print("[bold yellow]Uncertainty Notes[/bold yellow]")
        for note in bundle.uncertainty["notes"][:5]:
            console.print(f"- {note}")


# ---------------------------------------------------------------------------
# manifest
# ---------------------------------------------------------------------------


@main.command()
@click.option("--json-output", is_flag=True, default=False)
def manifest(json_output: bool) -> None:
    """Print the full MetaOntology OS grammar."""
    from opencrab.grammar.validator import describe_grammar

    grammar = describe_grammar()

    if json_output:
        click.echo(json.dumps(grammar, indent=2))
        return

    console.print(
        Panel(
            "[bold magenta]MetaOntology OS Grammar[/bold magenta]",
            subtitle="OpenCrab",
        )
    )

    # Spaces
    table = Table(title="Spaces", show_header=True)
    table.add_column("Space ID", style="cyan bold")
    table.add_column("Node Types", style="green")
    table.add_column("Description")
    for space_id, spec in grammar["spaces"].items():
        table.add_row(
            space_id,
            ", ".join(spec["node_types"]),
            spec["description"],
        )
    console.print(table)

    # Meta-edges
    edge_table = Table(title="Meta-Edges", show_header=True)
    edge_table.add_column("From", style="cyan")
    edge_table.add_column("To", style="green")
    edge_table.add_column("Relations")
    for edge in grammar["meta_edges"]:
        edge_table.add_row(
            edge["from_space"],
            edge["to_space"],
            ", ".join(edge["relations"]),
        )
    console.print(edge_table)

    # Impact categories
    impact_table = Table(title="Impact Categories", show_header=True)
    impact_table.add_column("ID", style="yellow bold")
    impact_table.add_column("Name", style="cyan")
    impact_table.add_column("Question")
    for cat in grammar["impact_categories"]:
        impact_table.add_row(cat["id"], cat["name"], cat["question"])
    console.print(impact_table)

    # ReBAC
    rebac = grammar["rebac"]
    console.print(
        Panel(
            f"[bold]Object types:[/bold] {', '.join(rebac['object_types'])}\n"
            f"[bold]Permissions:[/bold] {', '.join(rebac['permissions'])}",
            title="ReBAC",
        )
    )


# ---------------------------------------------------------------------------
# stage-node
# ---------------------------------------------------------------------------


@main.command()
@click.argument("space")
@click.argument("node_type")
@click.argument("node_id")
@click.option("--property", "properties", multiple=True, help="KEY=VALUE metadata.")
@click.option("--json-output", is_flag=True, default=False, help="Output raw JSON.")
def stage_node(
    space: str,
    node_type: str,
    node_id: str,
    properties: tuple[str, ...],
    json_output: bool,
) -> None:
    """Stage a node write without publishing it to canonical truth yet."""
    from opencrab.config import get_settings
    from opencrab.stores.factory import make_sql_store

    cfg = get_settings()
    sql = make_sql_store(cfg)
    payload = _parse_property_pairs(properties)
    stage_id = sql.stage_node(space, node_type, node_id, payload)
    result = {
        "stage_id": stage_id,
        "entry_type": "node",
        "status": "draft",
        "payload": {
            "space": space,
            "node_type": node_type,
            "node_id": node_id,
            "properties": payload,
        },
    }

    if json_output:
        click.echo(json.dumps(result, indent=2, default=str))
        return

    console.print(f"[green]Staged node write[/green] {stage_id}")


# ---------------------------------------------------------------------------
# stage-edge
# ---------------------------------------------------------------------------


@main.command()
@click.argument("from_space")
@click.argument("from_id")
@click.argument("relation")
@click.argument("to_space")
@click.argument("to_id")
@click.option("--property", "properties", multiple=True, help="KEY=VALUE metadata.")
@click.option("--json-output", is_flag=True, default=False, help="Output raw JSON.")
def stage_edge(
    from_space: str,
    from_id: str,
    relation: str,
    to_space: str,
    to_id: str,
    properties: tuple[str, ...],
    json_output: bool,
) -> None:
    """Stage an edge write without publishing it to canonical truth yet."""
    from opencrab.config import get_settings
    from opencrab.stores.factory import make_sql_store

    cfg = get_settings()
    sql = make_sql_store(cfg)
    payload = _parse_property_pairs(properties)
    stage_id = sql.stage_edge(from_space, from_id, relation, to_space, to_id, payload)
    result = {
        "stage_id": stage_id,
        "entry_type": "edge",
        "status": "draft",
        "payload": {
            "from_space": from_space,
            "from_id": from_id,
            "relation": relation,
            "to_space": to_space,
            "to_id": to_id,
            "properties": payload,
        },
    }

    if json_output:
        click.echo(json.dumps(result, indent=2, default=str))
        return

    console.print(f"[green]Staged edge write[/green] {stage_id}")


# ---------------------------------------------------------------------------
# list-staged
# ---------------------------------------------------------------------------


@main.command()
@click.option("--status-filter", default=None, help="Optional stage status filter.")
@click.option("--limit", default=20, show_default=True)
@click.option("--json-output", is_flag=True, default=False, help="Output raw JSON.")
def list_staged(status_filter: str | None, limit: int, json_output: bool) -> None:
    """List staged write operations."""
    from opencrab.config import get_settings
    from opencrab.stores.factory import make_sql_store

    cfg = get_settings()
    sql = make_sql_store(cfg)
    items = sql.list_staged_operations(status=status_filter, limit=limit)

    if json_output:
        click.echo(json.dumps(items, indent=2, default=str))
        return

    if not items:
        console.print("[yellow]No staged operations found.[/yellow]")
        return

    table = Table(title="Staged Operations", show_header=True, header_style="bold blue")
    table.add_column("Stage ID", style="bold")
    table.add_column("Type")
    table.add_column("Status")
    table.add_column("Target")
    for item in items:
        table.add_row(
            item["stage_id"],
            item["entry_type"],
            item["status"],
            _format_staged_target(item),
        )
    console.print(table)


# ---------------------------------------------------------------------------
# publish-stage
# ---------------------------------------------------------------------------


@main.command()
@click.argument("stage_id")
@click.option("--json-output", is_flag=True, default=False, help="Output raw JSON.")
def publish_stage(stage_id: str, json_output: bool) -> None:
    """Publish one staged write into canonical truth."""
    from opencrab.config import get_settings
    from opencrab.ontology.builder import OntologyBuilder
    from opencrab.stores.factory import make_doc_store, make_graph_store, make_sql_store

    cfg = get_settings()
    graph = make_graph_store(cfg)
    docs = make_doc_store(cfg)
    sql = make_sql_store(cfg)
    staged = sql.get_staged_operation(stage_id)
    if staged is None:
        raise click.ClickException(f"Unknown stage_id: {stage_id}")

    if staged["status"] != "draft":
        result = {
            "stage_id": stage_id,
            "status": staged["status"],
            "publish_result": staged["publish_result"],
        }
        if json_output:
            click.echo(json.dumps(result, indent=2, default=str))
            return
        console.print(f"[yellow]Stage {stage_id} is already {staged['status']}[/yellow]")
        return

    builder = OntologyBuilder(graph, docs, sql)
    payload = staged["payload"]
    try:
        if staged["entry_type"] == "node":
            publish_result = builder.add_node(
                space=str(payload["space"]),
                node_type=str(payload["node_type"]),
                node_id=str(payload["node_id"]),
                properties=dict(payload.get("properties") or {}),
            )
        else:
            publish_result = builder.add_edge(
                from_space=str(payload["from_space"]),
                from_id=str(payload["from_id"]),
                relation=str(payload["relation"]),
                to_space=str(payload["to_space"]),
                to_id=str(payload["to_id"]),
                properties=dict(payload.get("properties") or {}),
            )
    except Exception as exc:
        publish_result = {"error": str(exc), "stores": {"graph": f"error: {exc}"}}

    if publish_result.get("stores", {}).get("graph") == "ok":
        sql.mark_staged_published(stage_id, publish_result)
        final_status = "published"
    else:
        sql.mark_staged_failed(stage_id, publish_result)
        final_status = "failed"

    result = {
        "stage_id": stage_id,
        "status": final_status,
        "publish_result": publish_result,
    }
    if json_output:
        click.echo(json.dumps(result, indent=2, default=str))
        return

    status_color = "green" if final_status == "published" else "red"
    console.print(f"[{status_color}]Stage {stage_id} -> {final_status}[/{status_color}]")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _bundle_payload(
    question: str,
    bundle: Any,
    spaces: list[str] | None,
    project: str | None,
    source_id_prefix: str | None,
) -> dict[str, Any]:
    confirmed_facts = sum(1 for fact in bundle.facts if fact.status == "confirmed")
    inferred_facts = sum(1 for fact in bundle.facts if fact.status == "inferred")
    return {
        "question": question,
        "spaces_filter": spaces,
        "project_filter": project,
        "source_id_prefix_filter": source_id_prefix,
        "graph_expansion": bundle.scope["graph_expansion_enabled"],
        "total": len(bundle.facts),
        "confirmed_facts": confirmed_facts,
        "inferred_facts": inferred_facts,
        "supporting_evidence_count": len(bundle.supporting_evidence),
        "provenance_path_count": len(bundle.provenance_paths),
        "missing_link_count": len(bundle.missing_links),
        "results": bundle.legacy_results(),
        "context": bundle.to_dict(),
    }


def _find_supporting_evidence(bundle: Any, fact: Any) -> Any | None:
    source_id = str(fact.metadata.get("source_id") or "")
    for evidence in bundle.supporting_evidence:
        if source_id and evidence.ref == source_id:
            return evidence
        if fact.node_id and evidence.ref == fact.node_id:
            return evidence
    return None


def _find_provenance_paths(bundle: Any, fact: Any) -> list[Any]:
    target = str(fact.node_id or "")
    if not target:
        return []
    return [path for path in bundle.provenance_paths if target in path.nodes]


def _parse_property_pairs(items: tuple[str, ...]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for item in items:
        if "=" not in item:
            raise click.ClickException(f"Invalid property '{item}'. Use KEY=VALUE.")
        key, value = item.split("=", 1)
        payload[key] = _parse_scalar(value)
    return payload


def _parse_scalar(value: str) -> Any:
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def _format_staged_target(item: dict[str, Any]) -> str:
    payload = dict(item.get("payload") or {})
    if item.get("entry_type") == "node":
        return f"{payload.get('space')}/{payload.get('node_id')}"
    return (
        f"{payload.get('from_space')}/{payload.get('from_id')}"
        f" -[{payload.get('relation')}]-> "
        f"{payload.get('to_space')}/{payload.get('to_id')}"
    )


def _build_doctor_report(cfg: Any) -> dict[str, Any]:
    from opencrab.stores.factory import (
        make_doc_store,
        make_graph_store,
        make_sql_store,
        make_vector_store,
    )

    graph = make_graph_store(cfg)
    docs = make_doc_store(cfg)
    sql = make_sql_store(cfg)
    vector = make_vector_store(cfg)

    stores: list[dict[str, Any]] = []
    degraded_reasons: list[str] = []

    graph_notes = [f"nodes={graph.count_nodes()}"] if graph.available else ["unavailable"]
    sql_counts = sql.table_counts() if sql.available else {}
    docs_notes = (
        [
            f"node_docs={sql_counts.get('node_documents', 0)}",
            f"sources={sql_counts.get('source_documents', 0)}",
            f"staged={sql_counts.get('staged_operations', 0)}",
        ]
        if sql.available
        else ["unavailable"]
    )
    vector_notes = [f"vectors={vector.count()}"] if vector.available else ["unavailable"]

    store_specs = [
        ("graph", "Graph (LadybugDB)", graph, graph_notes),
        ("documents", "Documents + Registry (DuckDB)", docs, docs_notes),
        ("vectors", "Vectors (ChromaDB)", vector, vector_notes),
    ]
    for key, label, store, notes in store_specs:
        available = bool(store.available)
        ping = bool(store.ping()) if available else False
        stores.append(
            {
                "key": key,
                "label": label,
                "available": available,
                "ping": ping,
                "notes": notes,
            }
        )
        if not available:
            degraded_reasons.append(f"{label} is unavailable.")
        elif not ping:
            degraded_reasons.append(f"{label} connected but ping failed.")

    smoke = _run_isolated_closure_smoke()
    if not smoke["passed"]:
        degraded_reasons.append("Isolated closure smoke did not complete successfully.")

    counts = {
        "graph.nodes": graph.count_nodes() if graph.available else 0,
        "duckdb.node_documents": sql_counts.get("node_documents", 0),
        "duckdb.source_documents": sql_counts.get("source_documents", 0),
        "duckdb.audit_log": sql_counts.get("audit_log", 0),
        "duckdb.ontology_nodes": sql_counts.get("ontology_nodes", 0),
        "duckdb.ontology_edges": sql_counts.get("ontology_edges", 0),
        "duckdb.staged_operations": sql_counts.get("staged_operations", 0),
        "chroma.vectors": vector.count() if vector.available else 0,
    }

    return {
        "local_data_dir": cfg.local_data_dir,
        "stores": stores,
        "counts": counts,
        "closure_smoke": smoke,
        "degraded_reasons": degraded_reasons,
    }


def _run_isolated_closure_smoke() -> dict[str, Any]:
    from opencrab.config import Settings
    from opencrab.ontology.builder import OntologyBuilder
    from opencrab.ontology.context_pipeline import AgentContextPipeline, AgentContextRequest
    from opencrab.ontology.query import HybridQuery
    from opencrab.stores.factory import (
        make_doc_store,
        make_graph_store,
        make_sql_store,
        make_vector_store,
        reset_store_caches,
    )

    temp_dir_obj = tempfile.TemporaryDirectory(
        prefix="little-crab-doctor-",
        ignore_cleanup_errors=True,
    )
    temp_dir = temp_dir_obj.name
    try:
        smoke_cfg = Settings(
            STORAGE_MODE="local",
            LOCAL_DATA_DIR=temp_dir,
            CHROMA_COLLECTION="doctor_smoke_vectors",
        )
        graph = make_graph_store(smoke_cfg)
        docs = make_doc_store(smoke_cfg)
        sql = make_sql_store(smoke_cfg)
        vector = make_vector_store(smoke_cfg)
        builder = OntologyBuilder(graph, docs, sql)
        hybrid = HybridQuery(vector, graph)
        pipeline = AgentContextPipeline(hybrid, docs, sql)

        node_id = "doctor-smoke-doc"
        source_id = "doctor://smoke"
        text = "Doctor smoke runtime closure document about cache ttl and reliability."

        node_result = builder.add_node(
            "resource",
            "Document",
            node_id,
            {
                "name": "Doctor Smoke Runtime Document",
                "description": "Ephemeral runtime closure smoke node.",
            },
        )
        ingest_result = hybrid.ingest(
            text=text,
            source_id=source_id,
            metadata={"space": "resource", "node_id": node_id},
        )
        if docs.available:
            docs.upsert_source(
                source_id,
                text,
                {"space": "resource", "node_id": node_id},
            )
        bundle = pipeline.build_context(
            AgentContextRequest(question="doctor smoke runtime closure", limit=5)
        )
        query_match = any(fact.node_id == node_id for fact in bundle.facts)
        passed = (
            node_result.get("stores", {}).get("graph") == "ok"
            and str(ingest_result.get("stores", {}).get("vectors", "")).startswith("ok")
            and query_match
        )
        return {
            "passed": passed,
            "node_write_status": node_result.get("stores", {}).get("graph", "unknown"),
            "vector_ingest_status": ingest_result.get("stores", {}).get("vectors", "unknown"),
            "query_match": query_match,
            "supporting_evidence_count": len(bundle.supporting_evidence),
        }
    except Exception as exc:
        return {
            "passed": False,
            "node_write_status": f"error: {exc}",
            "vector_ingest_status": "not_run",
            "query_match": False,
            "supporting_evidence_count": 0,
        }
    finally:
        reset_store_caches()
        temp_dir_obj.cleanup()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    main()
