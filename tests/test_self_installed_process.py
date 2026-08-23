"""Regression checks for this repository acting as a template consumer."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_repository_carries_the_rendered_payload() -> None:
    """Keep one representative artifact from every delivered process layer."""
    expected = (
        ".copier-answers.yml",
        ".agents/orchestration/roles.yaml",
        ".agents/skills/implement-issue/SKILL.md",
        ".codex/hooks.json",
        ".claude/settings.json",
        ".github/workflows/ci.yml",
        ".githooks/pre-push",
        "AGENTS.md",
        "docs/architecture/agent-process.md",
        "scripts/ci_check.py",
    )
    missing = [path for path in expected if not (ROOT / path).is_file()]
    assert not missing, f"self-applied payload is missing: {', '.join(missing)}"


def test_pytest_has_a_single_configuration_home() -> None:
    """A bare pytest invocation needs the rendered root import path."""
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert not (ROOT / "pytest.ini").exists()
    assert "[tool.pytest.ini_options]" in pyproject
    assert 'pythonpath = ["."]' in pyproject


def test_default_render_keeps_document_guards_enabled(rendered_default: Path) -> None:
    """Only the self-hosting answers exclude its template source from document guards."""
    answers = yaml.safe_load((rendered_default / ".copier-answers.yml").read_text(encoding="utf-8"))
    assert answers["doc_guard_excluded_prefixes"] == []
