from __future__ import annotations

from pathlib import Path
import tomllib

from click.testing import CliRunner


def test_ingest_accepts_single_file_path(tmp_path):
    from opencrab.cli import main

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
    assert "opencrab status" not in result.output
