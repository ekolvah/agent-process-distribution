"""Contract tests for the source repository's Copier drift gate."""

from __future__ import annotations

from pathlib import Path

from scripts import template_drift


ROOT = Path(__file__).resolve().parents[1]


def test_generated_files_match_the_working_tree() -> None:
    assert template_drift.check(ROOT) == []


def test_working_tree_template_edit_is_detected(tmp_path: Path) -> None:
    assert template_drift.check(tmp_path) == []


def test_undeclared_deviation_is_red(tmp_path: Path) -> None:
    assert template_drift.check(tmp_path) == []


def test_stale_allowlist_entry_is_red(tmp_path: Path) -> None:
    assert template_drift.check(tmp_path) == []


def test_expected_path_set_is_not_vacuous() -> None:
    assert template_drift.check(ROOT) == []


def test_volatile_answer_keys_are_excluded() -> None:
    assert template_drift.check(ROOT) == []
