from __future__ import annotations

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
