"""
little-crab CLI — Click command interface.

Commands:
  init      Create .env from template
  serve     Start the MCP server (stdio)
  status    Check all store connections
  ingest    Ingest files from a path
  query     Run a hybrid query
  manifest  Print the MetaOntology grammar
"""

from __future__ import annotations

import json
import logging
import shutil
import sys
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
        make_doc_store,
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
# ingest
# ---------------------------------------------------------------------------


@main.command()
@click.argument("path", type=click.Path(exists=True))
@click.option("--recursive", "-r", is_flag=True, default=False)
@click.option("--extension", "-e", default=".txt,.md,.py", show_default=True)
def ingest(path: str, recursive: bool, extension: str) -> None:
    """Ingest files from PATH into the ontology vector store."""
    from opencrab.config import get_settings
    from opencrab.ontology.query import HybridQuery
    from opencrab.stores.factory import (
        make_doc_store,
        make_graph_store,
        make_vector_store,
    )

    cfg = get_settings()
    chroma = make_vector_store(cfg)
    graph = make_graph_store(cfg)
    docs = make_doc_store(cfg)
    hybrid = HybridQuery(chroma, graph)

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

    ok_count = 0
    for file in files:
        try:
            text = file.read_text(encoding="utf-8", errors="ignore")
            if not text.strip():
                continue
            source_id = str(file.resolve())
            meta = {"source_path": str(file), "extension": file.suffix}

            hybrid.ingest(text=text, source_id=source_id, metadata=meta)

            if docs.available:
                docs.upsert_source(source_id, text, meta)

            ok_count += 1
            console.print(f"  [green]OK[/green] {file.name} ({len(text)} chars)")
        except Exception as exc:
            console.print(f"  [red]FAIL[/red] {file.name}: {exc}")

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
    """Run a hybrid query and print results."""
    from opencrab.config import get_settings
    from opencrab.ontology.query import HybridQuery
    from opencrab.stores.factory import make_graph_store, make_vector_store

    cfg = get_settings()
    chroma = make_vector_store(cfg)
    graph = make_graph_store(cfg)
    hybrid = HybridQuery(chroma, graph)

    space_filter = [s.strip() for s in spaces.split(",")] if spaces else None

    results = hybrid.query(
        question=question,
        spaces=space_filter,
        limit=limit,
        project=project,
        source_id_prefix=source_id_prefix,
    )

    if json_output:
        click.echo(json.dumps([r.to_dict() for r in results], indent=2, default=str))
        return

    if not results:
        console.print("[yellow]No results found.[/yellow]")
        return

    console.print(f"\n[bold]Query:[/bold] {question}")
    if project:
        console.print(f"[dim]Project filter: {project}[/dim]")
    if source_id_prefix:
        console.print(f"[dim]Source prefix filter: {source_id_prefix}[/dim]")
    console.print(f"[dim]Found {len(results)} result(s)[/dim]\n")

    for i, result in enumerate(results, 1):
        console.print(
            f"[bold cyan]{i}.[/bold cyan] "
            f"[{result.source}] "
            f"node={result.node_id or '?'} "
            f"score={result.score:.3f}"
        )
        if result.text:
            preview = result.text[:200].replace("\n", " ")
            console.print(f"   [dim]{preview}...[/dim]")
        console.print()


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
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    main()
