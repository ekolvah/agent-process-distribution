"""Structural ownership contract for the publisher/consumer test split (issue #20).

Publisher-only tests live under ``tests/publisher/`` and never render to a
consumer. Consumer tests originate under ``template/tests/agent_process/``
and render below the reserved ``tests/agent_process/`` subtree. No process
test may remain loose directly under either ``tests/`` root.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from test_project_bootstrap_template import render

ROOT = Path(__file__).resolve().parents[2]
RECLASSIFIED_PUBLISHER_BASENAMES = (
    "test_hooks.py",
    "test_codex_hooks.py",
)
# main's tip immediately before issue #20's publisher/consumer split
# (c89457c "ci: recognize current Codex clean-comment wording (#51)") — the
# last commit with every process test loose under a flat tests/ root. Pinned
# rather than computed via `git merge-base HEAD origin/main`: once this PR
# merges, a later PR's origin/main already contains the split, so a dynamic
# merge-base would silently resolve to an already-migrated commit and stop
# exercising the flat-layout migration these tests exist to cover.
_PRE_MIGRATION_BASELINE_SHA = "c89457c06915d403fe40fa92c1cd6838da53a899"  # pragma: allowlist secret


def _direct_test_files(directory: Path) -> list[Path]:
    if not directory.is_dir():
        return []
    return sorted(
        path for path in directory.iterdir() if path.is_file() and path.name.startswith("test_")
    )


def _run(command: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def _resolve_pre_migration_baseline() -> str:
    """Make ``_PRE_MIGRATION_BASELINE_SHA`` locally available and return it.

    A CI checkout of the PR alone is shallow and single-ref: that commit
    object is absent locally until fetched directly. A silent absence here
    would previously reach copier as ``--vcs-ref ""``, which copier accepts
    as "no ref" (i.e. the current worktree) — so the fetch result is asserted
    rather than swallowed, and the two migration tests below run against the
    intended flat-layout baseline or fail loud, never a silently wrong one.
    """
    if (
        _run(
            ["git", "cat-file", "-e", f"{_PRE_MIGRATION_BASELINE_SHA}^{{commit}}"], cwd=ROOT
        ).returncode
        != 0
    ):
        completed = _run(
            ["git", "fetch", "--depth=1", "origin", _PRE_MIGRATION_BASELINE_SHA], cwd=ROOT
        )
        assert completed.returncode == 0, completed.stdout + completed.stderr
    return _PRE_MIGRATION_BASELINE_SHA


def _git_commit_all(destination: Path) -> None:
    for command in (
        ["git", "init", "-q"],
        ["git", "config", "user.email", "test@example.com"],
        ["git", "config", "user.name", "Test"],
        ["git", "add", "--all"],
        ["git", "commit", "-q", "-m", "initial"],
    ):
        completed = _run(command, cwd=destination)
        assert completed.returncode == 0, completed.stdout + completed.stderr


def test_every_process_test_has_exactly_one_physical_owner() -> None:
    loose_root = _direct_test_files(ROOT / "tests")
    loose_template = _direct_test_files(ROOT / "template" / "tests")
    assert loose_root == [], f"loose process test files directly under tests/: {loose_root}"
    assert loose_template == [], (
        f"loose process test files directly under template/tests/: {loose_template}"
    )
    assert (ROOT / "tests" / "publisher").is_dir(), "tests/publisher/ must exist"
    assert (ROOT / "template" / "tests" / "agent_process").is_dir(), (
        "template/tests/agent_process/ must exist"
    )


def test_publisher_tests_are_absent_from_a_clean_render(tmp_path: Path) -> None:
    destination = render(tmp_path)
    assert not (destination / "tests" / "publisher").exists()
    for name in RECLASSIFIED_PUBLISHER_BASENAMES:
        matches = list(destination.rglob(name))
        assert matches == [], f"{name} must not ship to a consumer, found: {matches}"


def test_consumer_tests_render_only_under_the_reserved_subtree(tmp_path: Path) -> None:
    destination = render(tmp_path)
    rendered_tests = destination / "tests"
    loose = _direct_test_files(rendered_tests)
    assert loose == [], f"process tests rendered loose at tests/ root: {loose}"
    consumer_subtree = rendered_tests / "agent_process"
    assert consumer_subtree.is_dir()
    assert list(consumer_subtree.glob("test_*.py")), "consumer subtree must not be empty"


def test_nested_consumer_tests_resolve_the_rendered_repository_root(tmp_path: Path) -> None:
    destination = render(tmp_path)
    _git_commit_all(destination)
    completed = _run(
        [sys.executable, "-m", "pytest", "-q", "tests/agent_process/test_doc_links.py"],
        cwd=destination,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_rendered_consumer_suite_passes(tmp_path: Path) -> None:
    destination = render(tmp_path)
    assert (destination / "tests" / "agent_process").is_dir(), (
        "reserved consumer subtree must exist in the render"
    )
    _git_commit_all(destination)
    completed = _run([sys.executable, "-m", "pytest", "-q"], cwd=destination)
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_update_from_flat_layout_preserves_unrelated_product_tests(tmp_path: Path) -> None:
    baseline = _resolve_pre_migration_baseline()
    destination = tmp_path / "consumer"
    completed = _run(
        [
            sys.executable,
            "-m",
            "copier",
            "copy",
            str(ROOT),
            str(destination),
            "--vcs-ref",
            baseline,
            "--defaults",
            "--trust",
            "-q",
        ],
        cwd=ROOT,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr

    product_test = destination / "tests" / "test_my_product_feature.py"
    product_test.write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    _git_commit_all(destination)

    completed = _run(
        [
            sys.executable,
            "-m",
            "copier",
            "update",
            "--vcs-ref",
            "HEAD",
            "--defaults",
            "--trust",
            "--conflict",
            "rej",
            "-q",
        ],
        cwd=destination,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr

    assert product_test.is_file()
    assert product_test.read_text(encoding="utf-8") == "def test_ok():\n    assert True\n"
    assert not (destination / "tests" / "test_adr_records.py").exists()
    assert (destination / "tests" / "agent_process" / "test_adr_records.py").is_file()


def test_reserved_consumer_test_path_collision_is_visible(tmp_path: Path) -> None:
    baseline = _resolve_pre_migration_baseline()
    destination = tmp_path / "consumer"
    completed = _run(
        [
            sys.executable,
            "-m",
            "copier",
            "copy",
            str(ROOT),
            str(destination),
            "--vcs-ref",
            baseline,
            "--defaults",
            "--trust",
            "-q",
        ],
        cwd=ROOT,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr

    colliding_dir = destination / "tests" / "agent_process"
    colliding_dir.mkdir(parents=True, exist_ok=True)
    colliding_file = colliding_dir / "test_adr_records.py"
    colliding_file.write_text("# product-owned, unrelated to the template\n", encoding="utf-8")
    _git_commit_all(destination)

    completed = _run(
        [
            sys.executable,
            "scripts/check_consumer_test_collision.py",
            str(destination),
            "--vcs-ref",
            "HEAD",
        ],
        cwd=ROOT,
    )
    assert completed.returncode != 0, completed.stdout + completed.stderr
    assert "tests/agent_process/test_adr_records.py" in completed.stdout + completed.stderr
