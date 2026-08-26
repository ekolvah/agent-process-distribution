"""Contract tests for the source repository's Copier drift gate."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from scripts import template_drift

ROOT = Path(__file__).resolve().parents[1]
CHECKOUT_IGNORES = (
    *template_drift.ARTIFACT_DIRECTORIES,
    *(f"{prefix}*" for prefix in template_drift.ARTIFACT_DIRECTORY_PREFIXES),
)


def checkout(tmp_path: Path, *, root: Path = ROOT) -> Path:
    """Make an isolated source checkout whose edits do not touch this branch."""
    destination = tmp_path / "checkout"
    shutil.copytree(
        root,
        destination,
        ignore=shutil.ignore_patterns(*CHECKOUT_IGNORES),
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


def test_checkout_excludes_ignored_artifacts(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "tracked.txt").write_text("kept\n", encoding="utf-8")
    for artifact in (".venv", "pytest-cache-files-repro"):
        directory = source / artifact
        directory.mkdir()
        (directory / "artifact.txt").write_text("ignored\n", encoding="utf-8")

    copied = checkout(tmp_path / "destination", root=source)

    assert (copied / "tracked.txt").is_file()
    assert not (copied / ".venv").exists()
    assert not (copied / "pytest-cache-files-repro").exists()


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


def test_missing_source_only_copier_requirement_is_red(
    tmp_path: Path, rendered_self_applied: Path
) -> None:
    source = checkout(tmp_path)
    requirements = source / "requirements-dev.in"
    requirements.write_text(
        requirements.read_text(encoding="utf-8").replace("copier\n", ""), encoding="utf-8"
    )

    report = template_drift.compare(
        source, rendered_self_applied, template_drift.load_allowlist(source)
    )

    assert "missing source-only Copier requirement: requirements-dev.in" in report.errors


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

    report = template_drift.compare(
        source, rendered_self_applied, template_drift.load_allowlist(source)
    )

    assert not any(
        "content differs: scripts/project_settings.py" in error for error in report.errors
    ), report.format()


def test_stale_expected_difference_entry_is_red(
    tmp_path: Path, rendered_self_applied: Path
) -> None:
    source = checkout(tmp_path)
    (source / "scripts" / "project_settings.py").write_text(
        (rendered_self_applied / "scripts" / "project_settings.py").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    report = template_drift.compare(
        source, rendered_self_applied, template_drift.load_allowlist(source)
    )

    assert "stale expected-difference allowlist entry: scripts/project_settings.py" in report.errors


def test_source_only_copier_requirement_is_allowed(
    tmp_path: Path, rendered_self_applied: Path
) -> None:
    source = checkout(tmp_path)
    report = template_drift.compare(
        source, rendered_self_applied, template_drift.load_allowlist(source)
    )

    assert not any("requirements-dev" in error for error in report.errors), report.format()


def test_unexpected_requirement_edit_is_red(tmp_path: Path, rendered_self_applied: Path) -> None:
    source = checkout(tmp_path)
    requirements = source / "requirements-dev.in"
    requirements.write_text(
        requirements.read_text(encoding="utf-8") + "unrelated-requirement\n",
        encoding="utf-8",
    )

    report = template_drift.compare(
        source, rendered_self_applied, template_drift.load_allowlist(source)
    )

    assert any("content differs: requirements-dev.in" in error for error in report.errors), (
        report.format()
    )


def test_undeclared_extra_file_is_red(tmp_path: Path, rendered_self_applied: Path) -> None:
    source = checkout(tmp_path)
    (source / "scripts" / "stray.py").write_text("stray\n", encoding="utf-8")

    report = template_drift.compare(
        source, rendered_self_applied, template_drift.load_allowlist(source)
    )

    assert "undeclared extra file: scripts/stray.py" in report.errors, report.format()


def test_orphaned_generated_copy_is_red(tmp_path: Path) -> None:
    source = checkout(tmp_path)
    (source / "template" / "tests" / "test_review_gate.py").unlink()

    report = template_drift.check(source)

    assert "undeclared extra file: tests/test_review_gate.py" in report.errors, report.format()


def test_nested_payload_directory_is_compared(tmp_path: Path, rendered_self_applied: Path) -> None:
    source = checkout(tmp_path)
    skill = source / ".agents" / "skills" / "plan-issue" / "agents" / "openai.yaml"
    skill.write_text("answer: drifted\n", encoding="utf-8")

    report = template_drift.compare(
        source, rendered_self_applied, template_drift.load_allowlist(source)
    )

    assert any(
        ".agents/skills/plan-issue/agents/openai.yaml" in error for error in report.errors
    ), report.format()


def test_top_level_payload_directory_is_compared(
    tmp_path: Path, rendered_self_applied: Path
) -> None:
    source = checkout(tmp_path)
    rendered = tmp_path / "rendered"
    shutil.copytree(rendered_self_applied, rendered)
    generated = rendered / "agents" / "consumer.yaml"
    generated.parent.mkdir(exist_ok=True)
    generated.write_text("name: consumer\n", encoding="utf-8")

    report = template_drift.compare(source, rendered, template_drift.load_allowlist(source))

    assert "missing generated file: agents/consumer.yaml" in report.errors, report.format()


def test_artifact_directories_are_excluded_at_any_depth(
    tmp_path: Path, rendered_self_applied: Path
) -> None:
    source = checkout(tmp_path)
    cache = source / "scripts" / "__pycache__"
    cache.mkdir()
    (cache / "junk.pyc").write_bytes(b"")

    report = template_drift.compare(
        source, rendered_self_applied, template_drift.load_allowlist(source)
    )

    assert not any("__pycache__" in error for error in report.errors), report.format()


def test_venv_directory_is_excluded_from_drift_scan(
    tmp_path: Path, rendered_self_applied: Path
) -> None:
    source = checkout(tmp_path)
    virtualenv = source / ".venv"
    virtualenv.mkdir()
    (virtualenv / "pyvenv.cfg").write_text("home = python\n", encoding="utf-8")

    report = template_drift.compare(
        source, rendered_self_applied, template_drift.load_allowlist(source)
    )

    assert not any(".venv" in error for error in report.errors), report.format()


def test_expected_path_set_is_not_vacuous(clean_drift_report: template_drift.DriftReport) -> None:
    assert clean_drift_report.errors == (), clean_drift_report.format()
    assert template_drift.REQUIRED_GENERATED_PATHS
    assert "scripts/ci_check.py" in template_drift.REQUIRED_GENERATED_PATHS
    assert ".claude/settings.json" in template_drift.REQUIRED_GENERATED_PATHS


def test_volatile_answer_keys_are_excluded() -> None:
    answers = template_drift.load_answers(ROOT)

    assert not template_drift.VOLATILE_ANSWER_KEYS & answers.keys()
