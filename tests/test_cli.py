from __future__ import annotations

import json
from pathlib import Path
import tomllib

from click.testing import CliRunner


def _reset_runtime() -> None:
    from opencrab.config import reset_settings_cache
    from opencrab.stores.factory import reset_store_caches

    reset_settings_cache()
    reset_store_caches()


def test_ingest_accepts_single_file_path(tmp_path):
    from opencrab.cli import main

    _reset_runtime()
    data_dir = tmp_path / "opencrab_data"
    doc = tmp_path / "note.md"
    doc.write_text("System performance is degrading because cache TTL is too low.")

    runner = CliRunner()
    result = runner.invoke(
        main,
        ["ingest", str(doc)],
        env={
            "STORAGE_MODE": "local",
            "LOCAL_DATA_DIR": str(data_dir),
            "CHROMA_COLLECTION": "test_single_file_ingest",
        },
    )

    assert result.exit_code == 0
    assert "Ingested 1/1 files." in result.output


def test_cli_entrypoint_aliases_are_declared() -> None:
    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    project = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    scripts = project["project"]["scripts"]

    assert scripts["littlecrab"] == "opencrab.cli:main"
    assert scripts["ltcrab"] == "opencrab.cli:main"
    assert scripts["little-crab"] == "opencrab.cli:main"
    assert scripts["opencrab"] == "opencrab.cli:main"


def test_init_guidance_prefers_littlecrab_command() -> None:
    from opencrab.cli import main

    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(main, ["init"])

    assert result.exit_code == 0
    assert "littlecrab status" in result.output
    assert "littlecrab serve" in result.output
    assert "ltcrab" in result.output
    assert "opencrab" in result.output
    assert "(deprecated)" in result.output
    assert "opencrab status" not in result.output


def test_doctor_json_output_reports_health_and_closure_smoke(tmp_path) -> None:
    from opencrab.cli import main

    _reset_runtime()
    data_dir = tmp_path / "opencrab_data"

    runner = CliRunner()
    result = runner.invoke(
        main,
        ["doctor", "--json-output"],
        env={
            "STORAGE_MODE": "local",
            "LOCAL_DATA_DIR": str(data_dir),
            "CHROMA_COLLECTION": "test_doctor_runtime",
        },
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["local_data_dir"] == str(data_dir)
    assert payload["closure_smoke"]["passed"] is True
    assert "duckdb.staged_operations" in payload["counts"]
    assert payload["counts"]["duckdb.staged_operations"] == 0


def test_query_json_output_includes_trustability_counts(tmp_path) -> None:
    from opencrab.cli import main

    _reset_runtime()
    data_dir = tmp_path / "opencrab_data"
    doc = tmp_path / "note.md"
    doc.write_text("Cache TTL tuning improved reliability for the analytics system.")
    env = {
        "STORAGE_MODE": "local",
        "LOCAL_DATA_DIR": str(data_dir),
        "CHROMA_COLLECTION": "test_query_trustability",
    }

    runner = CliRunner()
    ingest_result = runner.invoke(main, ["ingest", str(doc)], env=env)
    assert ingest_result.exit_code == 0

    query_result = runner.invoke(main, ["query", "cache ttl reliability", "--json-output"], env=env)
    assert query_result.exit_code == 0

    payload = json.loads(query_result.output)
    assert payload["total"] >= 1
    assert payload["confirmed_facts"] >= 1
    assert "supporting_evidence_count" in payload
    assert "provenance_path_count" in payload
    assert "context" in payload


def test_stage_node_and_publish_stage_flow(tmp_path) -> None:
    from opencrab.cli import main

    _reset_runtime()
    data_dir = tmp_path / "opencrab_data"
    env = {
        "STORAGE_MODE": "local",
        "LOCAL_DATA_DIR": str(data_dir),
        "CHROMA_COLLECTION": "test_stage_publish",
    }

    runner = CliRunner()
    stage_result = runner.invoke(
        main,
        [
            "stage-node",
            "resource",
            "Document",
            "doc-1",
            "--property",
            "name=Staged Doc",
            "--json-output",
        ],
        env=env,
    )
    assert stage_result.exit_code == 0
    staged = json.loads(stage_result.output)
    assert staged["status"] == "draft"

    list_result = runner.invoke(main, ["list-staged", "--json-output"], env=env)
    assert list_result.exit_code == 0
    listed = json.loads(list_result.output)
    assert listed[0]["stage_id"] == staged["stage_id"]

    publish_result = runner.invoke(
        main,
        ["publish-stage", staged["stage_id"], "--json-output"],
        env=env,
    )
    assert publish_result.exit_code == 0
    published = json.loads(publish_result.output)
    assert published["status"] == "published"
    assert published["publish_result"]["stores"]["graph"] == "ok"
    assert published["publish_result"]["stores"]["registry"] == "ok"
