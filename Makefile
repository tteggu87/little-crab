.PHONY: help install dev-install status serve query manifest lint format test coverage seed test-py312 coverage-py312 dogfood-mcp verify-intelligence

PYTHON := python
PIP    := pip
PYTEST := pytest

help:
	@echo "little-crab - local-first ontology MCP runtime"
	@echo ""
	@echo "Usage:"
	@echo "  make install       Install package"
	@echo "  make dev-install   Install with dev extras"
	@echo "  make status        Check store connections"
	@echo "  make serve         Start MCP server on stdio"
	@echo "  make manifest      Print MetaOntology grammar"
	@echo "  make seed          Seed embedded local runtime"
	@echo "  make lint          Run ruff linter"
	@echo "  make format        Run black + isort"
	@echo "  make test          Run test suite"
	@echo "  make test-py312    Run canonical Python 3.12 test suite"
	@echo "  make verify-intelligence  Check intelligence manifests against live code"
	@echo "  make coverage      Run tests with coverage report"
	@echo "  make dogfood-mcp   Run local stdio MCP dogfood scenarios"

install:
	$(PIP) install -e .

dev-install:
	$(PIP) install -e ".[dev]"

status:
	$(PYTHON) -m opencrab.cli status

serve:
	$(PYTHON) -m opencrab.cli serve

manifest:
	$(PYTHON) -m opencrab.cli manifest

seed:
	$(PYTHON) scripts/seed_ontology.py

lint:
	ruff check opencrab tests

format:
	black opencrab tests scripts
	isort opencrab tests scripts

test:
	$(PYTEST) tests/ -v

test-py312:
	py -3.12 -m pytest tests/test_cli.py tests/test_mcp.py tests/test_stores.py

verify-intelligence:
	$(PYTHON) scripts/verify_repo_intelligence.py

coverage:
	$(PYTEST) tests/ --cov=opencrab --cov-report=term-missing --cov-report=html
	@echo "HTML report: htmlcov/index.html"

coverage-py312:
	py -3.12 -m pytest tests/ --cov=opencrab --cov-report=term-missing --cov-report=html
	@echo "HTML report: htmlcov/index.html"

dogfood-mcp:
	py -3.12 scripts/dogfood_mcp.py
