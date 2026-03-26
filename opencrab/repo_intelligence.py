"""Repository-level intelligence verification helpers."""

from __future__ import annotations

import inspect
import re
from pathlib import Path
from typing import Any

import yaml

from opencrab.cli import main as cli_main
from opencrab.mcp.tools import _TOOL_FUNCTIONS
from opencrab.stores.duckdb_store import DuckDBStore

SCRIPT_ACTION_IMPLEMENTATIONS: dict[str, str] = {
    "script.seed": "scripts.seed_ontology:seed",
    "script.dogfood_mcp": "scripts.dogfood_mcp:main",
    "script.verify_repo_intelligence": "scripts.verify_repo_intelligence:main",
}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _action_list_to_map(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {item["key"]: item for item in items}


def discover_cli_actions() -> dict[str, str]:
    actions: dict[str, str] = {}
    for command_name, command in cli_main.commands.items():
        callback = getattr(command, "callback", None)
        if callback is None:
            continue
        actions[f"cli.{command_name}"] = f"{callback.__module__}:{callback.__name__}"
    return actions


def discover_mcp_actions() -> dict[str, str]:
    return {
        f"mcp.{tool_name}": f"{fn.__module__}:{fn.__name__}"
        for tool_name, fn in _TOOL_FUNCTIONS.items()
    }


def discover_script_actions() -> dict[str, str]:
    return dict(SCRIPT_ACTION_IMPLEMENTATIONS)


def discover_duckdb_tables() -> set[str]:
    source = inspect.getsource(DuckDBStore._create_tables)
    return set(re.findall(r"CREATE TABLE IF NOT EXISTS ([a-z_]+)", source))


def discover_contract_tables() -> set[str]:
    contract_path = repo_root() / "intelligence" / "schemas" / "duckdb_contracts.sql"
    contract = contract_path.read_text(encoding="utf-8")
    return set(re.findall(r"CREATE TABLE ([a-z_]+)", contract))


def load_intelligence_contracts() -> dict[str, Any]:
    root = repo_root() / "intelligence"
    return {
        "actions": _load_yaml(root / "manifests" / "actions.yaml"),
        "capabilities": _load_yaml(root / "registry" / "capabilities.yaml"),
        "datasets": _load_yaml(root / "manifests" / "datasets.yaml"),
        "handler": _load_yaml(root / "handlers" / "mcp_request.yaml"),
    }


def verify_repo_intelligence() -> list[str]:
    contracts = load_intelligence_contracts()

    action_items = contracts["actions"]["actions"]
    capability_items = contracts["capabilities"]["capabilities"]
    dataset_items = contracts["datasets"]["datasets"]
    handler = contracts["handler"]

    action_map = _action_list_to_map(action_items)
    capability_map = _action_list_to_map(capability_items)
    dataset_map = {item["dataset_key"]: item for item in dataset_items}

    actual_actions: dict[str, str] = {}
    actual_actions.update(discover_cli_actions())
    actual_actions.update(discover_mcp_actions())
    actual_actions.update(discover_script_actions())

    errors: list[str] = []

    if set(action_map) != set(actual_actions):
        missing = sorted(set(actual_actions) - set(action_map))
        extra = sorted(set(action_map) - set(actual_actions))
        if missing:
            errors.append(f"actions.yaml missing actions: {missing}")
        if extra:
            errors.append(f"actions.yaml has unknown actions: {extra}")

    for action_key, implementation in actual_actions.items():
        action = action_map.get(action_key)
        if action is None:
            continue

        if action.get("implementation") != implementation:
            errors.append(
                f"{action_key} implementation drift: "
                f"{action.get('implementation')} != {implementation}"
            )

        capability_key = action.get("capability")
        if capability_key not in capability_map:
            errors.append(f"{action_key} references missing capability {capability_key}")
        else:
            capability = capability_map[capability_key]
            if capability.get("implementation") != implementation:
                errors.append(
                    f"{capability_key} capability implementation drift: "
                    f"{capability.get('implementation')} != {implementation}"
                )

        for dataset_key in action.get("touches_datasets", []):
            if dataset_key not in dataset_map:
                errors.append(f"{action_key} references missing dataset {dataset_key}")

    declared_capability_keys = {item["capability"] for item in action_items}
    if set(capability_map) != declared_capability_keys:
        missing_caps = sorted(declared_capability_keys - set(capability_map))
        extra_caps = sorted(set(capability_map) - declared_capability_keys)
        if missing_caps:
            errors.append(f"capabilities.yaml missing keys: {missing_caps}")
        if extra_caps:
            errors.append(f"capabilities.yaml has unknown keys: {extra_caps}")

    for dataset_key, dataset in dataset_map.items():
        shape_path = repo_root() / dataset["canonical_shape"]
        if not shape_path.exists():
            errors.append(f"{dataset_key} points to missing canonical shape {shape_path}")
        for action_key in dataset.get("used_by_actions", []):
            if action_key not in action_map:
                errors.append(f"{dataset_key} references missing action {action_key}")

    duckdb_dataset_keys = {
        key.removeprefix("duckdb.") for key in dataset_map if key.startswith("duckdb.")
    }
    duckdb_tables = discover_duckdb_tables()
    contract_tables = discover_contract_tables()
    if duckdb_dataset_keys != duckdb_tables:
        missing_duckdb = sorted(duckdb_tables - duckdb_dataset_keys)
        extra_duckdb = sorted(duckdb_dataset_keys - duckdb_tables)
        if missing_duckdb:
            errors.append(f"datasets.yaml missing duckdb tables: {missing_duckdb}")
        if extra_duckdb:
            errors.append(f"datasets.yaml has unknown duckdb tables: {extra_duckdb}")

    if contract_tables != duckdb_tables:
        missing_contract = sorted(duckdb_tables - contract_tables)
        extra_contract = sorted(contract_tables - duckdb_tables)
        if missing_contract:
            errors.append(f"duckdb_contracts.sql missing tables: {missing_contract}")
        if extra_contract:
            errors.append(f"duckdb_contracts.sql has unknown tables: {extra_contract}")

    if "chroma.vectors" not in dataset_map:
        errors.append("datasets.yaml missing chroma.vectors")

    actual_mcp_action_order = list(discover_mcp_actions())
    handler_chain = [item["action"] for item in handler.get("chain", [])]
    if handler.get("emitted_by") != ["cli.serve"]:
        errors.append("mcp_request.yaml emitted_by must stay ['cli.serve']")
    if handler_chain != actual_mcp_action_order:
        errors.append(
            f"mcp_request.yaml chain drift: {handler_chain} != {actual_mcp_action_order}"
        )

    return errors

