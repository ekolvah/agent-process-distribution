"""Contract tests for the source repository's Copier drift gate."""

from __future__ import annotations

import shutil
from dataclasses import replace
from pathlib import Path

import pytest

from scripts import template_drift

ROOT = Path(__file__).resolve().parents[1]


def checkout(tmp_path: Path) -> Path:
    """Make an isolated source checkout whose edits do not touch this branch."""
    destination = tmp_path / "checkout"
    shutil.copytree(
        ROOT,
        destination,
        ignore=shutil.ignore_patterns(".git", ".pytest_cache", ".ruff_cache", "__pycache__"),
    )
    return destination


@pytest.fixture(scope="session")
def rendered_self_applied(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Render the unchanged working tree once for all comparison-only nodes."""
    return template_drift.render_working_tree(
        ROOT, tmp_path_factory.mktemp("working-tree-render") / "rendered"
    )


@pytest.fixture(scope="session")
def clean_drift_report(rendered_self_applied: Path) -> template_drift.DriftReport:
    return template_drift.compare(ROOT, rendered_self_applied, template_drift.load_allowlist(ROOT))


def test_generated_files_match_the_working_tree(
    clean_drift_report: template_drift.DriftReport,
) -> None:
    assert clean_drift_report.errors == (), clean_drift_report.format()


def test_working_tree_template_edit_is_detected(tmp_path: Path) -> None:
    source = checkout(tmp_path)
    (source / "template" / "scripts" / "ci_check.py.jinja").write_text(
        "uncommitted template edit\n", encoding="utf-8"
    )

    report = template_drift.check(source)

    assert any("scripts/ci_check.py" in error for error in report.errors), report.format()


def test_undeclared_deviation_is_red(tmp_path: Path, rendered_self_applied: Path) -> None:
    source = checkout(tmp_path)
    path = source / "scripts" / "ci_check.py"
    path.write_text(path.read_text(encoding="utf-8") + "\nundeclared drift\n", encoding="utf-8")

    report = template_drift.compare(
        source, rendered_self_applied, template_drift.load_allowlist(source)
    )

    assert any("scripts/ci_check.py" in error for error in report.errors), report.format()


def test_stale_allowlist_entry_is_red(tmp_path: Path, rendered_self_applied: Path) -> None:
    source = checkout(tmp_path)
    allowlist = replace(
        template_drift.load_allowlist(source),
        expected_to_differ_paths=frozenset({"scripts/check_red.py"}),
    )

    report = template_drift.compare(source, rendered_self_applied, allowlist)

    assert "stale expected-to-differ allowlist entry: scripts/check_red.py" in report.errors


def test_root_only_entry_with_a_template_origin_is_red(
    tmp_path: Path, rendered_self_applied: Path
) -> None:
    source = checkout(tmp_path)
    rendered = tmp_path / "rendered"
    shutil.copytree(rendered_self_applied, rendered)
    shutil.copy2(
        source / "tests" / "test_template_drift.py", rendered / "tests" / "test_template_drift.py"
    )

    report = template_drift.compare(source, rendered, template_drift.load_allowlist(source))

    assert "stale root-only allowlist entry: tests/test_template_drift.py" in report.errors


def test_declared_expected_difference_is_allowed(
    tmp_path: Path, rendered_self_applied: Path
) -> None:
    source = checkout(tmp_path)
    settings = source / "scripts" / "project_settings.py"
    settings.write_text(
        settings.read_text(encoding="utf-8") + "\nSOURCE_ONLY = True\n", encoding="utf-8"
    )
    allowlist = replace(
        template_drift.load_allowlist(source),
        expected_to_differ_paths=frozenset({"scripts/project_settings.py"}),
    )

    report = template_drift.compare(source, rendered_self_applied, allowlist)

    assert not any("scripts/project_settings.py" in error for error in report.errors), (
        report.format()
    )


def test_extra_file_in_a_strict_directory_is_red(
    tmp_path: Path, rendered_self_applied: Path
) -> None:
    source = checkout(tmp_path)
    (source / ".githooks" / "unexpected").write_text("extra\n", encoding="utf-8")

    report = template_drift.compare(
        source, rendered_self_applied, template_drift.load_allowlist(source)
    )

    assert "undeclared extra file in strict directory: .githooks/unexpected" in report.errors


def test_expected_path_set_is_not_vacuous(clean_drift_report: template_drift.DriftReport) -> None:
    assert clean_drift_report.errors == (), clean_drift_report.format()
    assert template_drift.REQUIRED_GENERATED_PATHS
    assert "scripts/ci_check.py" in template_drift.REQUIRED_GENERATED_PATHS
    assert ".claude/settings.json" in template_drift.REQUIRED_GENERATED_PATHS


def test_volatile_answer_keys_are_excluded() -> None:
    answers = template_drift.load_answers(ROOT)

    assert not template_drift.VOLATILE_ANSWER_KEYS & answers.keys()
