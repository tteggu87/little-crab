"""Repository intelligence contract tests."""

from opencrab.repo_intelligence import verify_repo_intelligence


def test_repo_intelligence_matches_live_code() -> None:
    errors = verify_repo_intelligence()
    assert errors == []
