"""Verify that repository intelligence manifests still match live code."""

from __future__ import annotations

from opencrab.repo_intelligence import (
    discover_cli_actions,
    discover_contract_tables,
    discover_duckdb_tables,
    discover_mcp_actions,
    discover_script_actions,
    verify_repo_intelligence,
)


def main() -> int:
    errors = verify_repo_intelligence()
    if errors:
        print("FAIL: repository intelligence drift detected.")
        for error in errors:
            print(f"- {error}")
        return 1

    cli_count = len(discover_cli_actions())
    mcp_count = len(discover_mcp_actions())
    script_count = len(discover_script_actions())
    duckdb_count = len(discover_duckdb_tables())
    contract_count = len(discover_contract_tables())

    print("PASS: repository intelligence matches live code.")
    print(
        "Verified "
        f"{cli_count} CLI actions, "
        f"{mcp_count} MCP actions, "
        f"{script_count} script actions, "
        f"{duckdb_count} DuckDB tables, "
        f"and {contract_count} canonical contract tables."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
