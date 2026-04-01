# Contributing

Thanks for helping improve little-crab.

## Development Setup

1. Install Python 3.11 or newer.
2. Create and activate a virtual environment.
3. Install the project with development dependencies.

```bash
python -m pip install -e ".[dev]"
```

4. Initialize local runtime settings when you need a local data directory.

```bash
littlecrab init
```

## Before Opening A PR

Run the core verification commands:

```bash
python -m pytest tests/test_cli.py tests/test_mcp.py tests/test_stores.py
python scripts/verify_repo_intelligence.py
```

If you change the MCP workflow or user-facing docs, also run:

```bash
python scripts/dogfood_mcp.py
```

If your Windows shell does not map `python` to Python 3.11+, use the launcher fallback instead:

```bash
py -3.12 -m pytest tests/test_cli.py tests/test_mcp.py tests/test_stores.py
py -3.12 scripts/verify_repo_intelligence.py
py -3.12 scripts/dogfood_mcp.py
```

## Contribution Guidelines

- Keep the project local-first.
- Preserve the OpenCrab grammar, validator behavior, and MCP tool names.
- Prefer narrow, explicit changes over broad redesigns.
- Update affected docs and repository intelligence in the same change.
- Call out any intentional compatibility exceptions in the PR description.
