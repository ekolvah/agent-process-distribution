"""Tests for `scripts/ci_check.py` — the pre-commit gate runner.

Covers `CHECKS` ↔ `ci.yml` step parity, module-discovery exclusions, runner exit
codes, and the capture-failure path that must name its real cause.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

from scripts import ci_check
from scripts.ci_check import _find_modules, _run, _tracked_files, run_selected

_CI_YML = (
    Path(__file__).resolve().parent.parent.parent
    / ".github"
    / "workflows"
    / "agent-process-quality.yml"
)


def _init_repo(tmp_path: Path) -> None:
    """A committed, clean repo — enough for `git rev-parse HEAD` and a stable status."""
    subprocess.run(["git", "init", "--quiet"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    (tmp_path / "tracked.py").write_text("tracked = True\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.py"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "--quiet", "-m", "init"], cwd=tmp_path, check=True)


def _head(tmp_path: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    ).stdout.strip()


def _quality_caller() -> dict[str, Any]:
    """Return the thin quality caller without letting it select checks."""
    spec = yaml.safe_load(_CI_YML.read_text(encoding="utf-8"))
    return spec["jobs"]["quality"]


class TestStepParity:
    """The core defect: ci.yml duplicated the check list by hand and drifted —
    some registry checks were silently missing in CI. The caller passes check names
    to the callee, so parity remains enforceable without copying workflow steps."""

    def test_ci_yml_cannot_select_a_subset_of_checks(self) -> None:
        assert "with" not in _quality_caller()

    def test_full_runner_visits_every_registered_check(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # A temporary repo, not the real one: `run_selected()` now consults
        # `.ci_check_stamp` at cwd, and this test must not read or write the
        # maintainer's own stamp file.
        _init_repo(tmp_path)
        monkeypatch.chdir(tmp_path)
        called: list[str] = []
        monkeypatch.setattr(
            ci_check,
            "CHECKS",
            {"first": lambda: called.append("first"), "second": lambda: called.append("second")},
        )

        run_selected()

        assert called == ["first", "second"]


class TestFindModules:
    @staticmethod
    def _repository_with_mypy_candidates(tmp_path: Path) -> None:
        subprocess.run(["git", "init", "--quiet"], cwd=tmp_path, check=True)
        (tmp_path / ".gitignore").write_text("evidence/\n", encoding="utf-8")
        (tmp_path / "tracked.py").write_text("tracked = True\n", encoding="utf-8")
        (tmp_path / "new_module.py").write_text("new = True\n", encoding="utf-8")
        evidence = tmp_path / "evidence"
        evidence.mkdir()
        (evidence / "planning_probe.py").write_text("probe = True\n", encoding="utf-8")
        subprocess.run(["git", "add", ".gitignore", "tracked.py"], cwd=tmp_path, check=True)

    def test_excludes_audit_tmp_and_pytest_cache(self) -> None:
        modules = set(_find_modules())
        assert (
            "scripts/ci_check.py".replace("/", "\\") in modules or "scripts/ci_check.py" in modules
        )
        assert not any(".audit-tmp" in m for m in modules)
        assert not any("pytest-cache-files-" in m for m in modules)

    def test_untracked_unignored_python_file_is_in_scope_before_git_add(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._repository_with_mypy_candidates(tmp_path)
        monkeypatch.chdir(tmp_path)

        assert "new_module.py" in _find_modules()

    def test_ignored_python_probe_is_out_of_scope(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._repository_with_mypy_candidates(tmp_path)
        monkeypatch.chdir(tmp_path)

        modules = {name.replace("\\", "/") for name in _find_modules()}
        assert "evidence/planning_probe.py" not in modules

    def test_tracked_python_files_remain_in_scope(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._repository_with_mypy_candidates(tmp_path)
        monkeypatch.chdir(tmp_path)

        assert "tracked.py" in _find_modules()

    def test_tracked_python_file_deleted_before_staging_is_out_of_scope(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._repository_with_mypy_candidates(tmp_path)
        (tmp_path / "tracked.py").unlink()
        monkeypatch.chdir(tmp_path)

        assert "tracked.py" not in _find_modules()


class TestStamp:
    """`.ci_check_stamp` lets a full run skip checks already verified for this
    exact, clean tree — see issue #43. Every test runs in a temporary repo
    (never the real one) since `run_selected()` now touches a stamp file at
    cwd.

    Not every case here is provable RED against unmodified `ci_check.py`:
    a "must not record" assertion is trivially true before the recording
    mechanism exists at all. Only the three positive-behavior tests
    (skip-when-verified, record-when-none, record-updates-on-mismatch) are
    run through `check_red.py`; the rest are regression guards for the
    control-flow guards added alongside the base mechanism, confirmed by a
    normal green run after implementation.
    """

    @pytest.fixture(autouse=True)
    def _no_ci_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # GitHub Actions sets `CI=true` for every job step, including this test
        # run itself — without clearing it, "not in CI" tests would silently pick
        # up the real CI branch and never observe the stamp read/write they check.
        monkeypatch.delenv("CI", raising=False)

    @staticmethod
    def _stamp(tmp_path: Path) -> Path:
        return tmp_path / ".ci_check_stamp"

    @staticmethod
    def _spy_checks() -> tuple[dict[str, Any], list[str]]:
        called: list[str] = []
        checks = {
            "first": lambda: called.append("first"),
            "second": lambda: called.append("second"),
        }
        return checks, called

    def test_full_run_skips_registered_checks_when_stamp_matches_clean_head(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _init_repo(tmp_path)
        monkeypatch.chdir(tmp_path)
        self._stamp(tmp_path).write_text(_head(tmp_path), encoding="utf-8")
        checks, called = self._spy_checks()
        monkeypatch.setattr(ci_check, "CHECKS", checks)

        run_selected()

        assert called == []

    def test_full_run_executes_and_records_stamp_when_none_exists(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _init_repo(tmp_path)
        monkeypatch.chdir(tmp_path)
        checks, called = self._spy_checks()
        monkeypatch.setattr(ci_check, "CHECKS", checks)

        run_selected()

        assert called == ["first", "second"]
        assert self._stamp(tmp_path).read_text(encoding="utf-8").strip() == _head(tmp_path)

    def test_full_run_executes_when_stamp_head_does_not_match(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _init_repo(tmp_path)
        monkeypatch.chdir(tmp_path)
        self._stamp(tmp_path).write_text("0" * 40, encoding="utf-8")
        checks, called = self._spy_checks()
        monkeypatch.setattr(ci_check, "CHECKS", checks)

        run_selected()

        assert called == ["first", "second"]
        assert self._stamp(tmp_path).read_text(encoding="utf-8").strip() == _head(tmp_path)

    def test_full_run_executes_when_working_tree_is_dirty_and_records_nothing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _init_repo(tmp_path)
        monkeypatch.chdir(tmp_path)
        (tmp_path / "tracked.py").write_text("tracked = False\n", encoding="utf-8")
        checks, called = self._spy_checks()
        monkeypatch.setattr(ci_check, "CHECKS", checks)

        run_selected()

        assert called == ["first", "second"]
        assert not self._stamp(tmp_path).exists()

    def test_full_run_does_not_record_stamp_when_a_check_fails(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _init_repo(tmp_path)
        monkeypatch.chdir(tmp_path)

        def failing() -> None:
            raise SystemExit(1)

        monkeypatch.setattr(ci_check, "CHECKS", {"first": failing})

        with pytest.raises(SystemExit):
            run_selected()

        assert not self._stamp(tmp_path).exists()

    def test_full_run_does_not_record_stamp_when_head_moves_during_run(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _init_repo(tmp_path)
        monkeypatch.chdir(tmp_path)
        original_head = _head(tmp_path)

        def moves_head() -> None:
            subprocess.run(
                ["git", "commit", "--quiet", "--allow-empty", "-m", "concurrent"],
                cwd=tmp_path,
                check=True,
            )

        monkeypatch.setattr(ci_check, "CHECKS", {"first": moves_head})

        run_selected()

        assert not self._stamp(tmp_path).exists()
        assert _head(tmp_path) != original_head

    def test_full_run_ignores_an_existing_stamp_under_ci_environment(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _init_repo(tmp_path)
        monkeypatch.chdir(tmp_path)
        self._stamp(tmp_path).write_text(_head(tmp_path), encoding="utf-8")
        monkeypatch.setenv("CI", "true")
        checks, called = self._spy_checks()
        monkeypatch.setattr(ci_check, "CHECKS", checks)

        run_selected()

        assert called == ["first", "second"]

    def test_full_run_does_not_record_a_stamp_under_ci_environment(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _init_repo(tmp_path)
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("CI", "true")
        checks, called = self._spy_checks()
        monkeypatch.setattr(ci_check, "CHECKS", checks)

        run_selected()

        assert called == ["first", "second"]
        # A fresh stamp appearing here would prove the record path ran despite
        # the CI guard — no stamp existed beforehand.
        assert not self._stamp(tmp_path).exists()

    def test_only_mode_neither_reads_nor_writes_the_stamp(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _init_repo(tmp_path)
        monkeypatch.chdir(tmp_path)
        self._stamp(tmp_path).write_text("0" * 40, encoding="utf-8")
        checks, called = self._spy_checks()
        monkeypatch.setattr(ci_check, "CHECKS", checks)

        run_selected(only="first")

        assert called == ["first"]
        assert self._stamp(tmp_path).read_text(encoding="utf-8").strip() == "0" * 40


class TestMypyManifest:
    def test_requests_cached_and_untracked_excluding_standard_ignores(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls: list[list[str]] = []
        (tmp_path / "tracked.py").write_text("tracked = True\n", encoding="utf-8")
        (tmp_path / "new_module.py").write_text("new = True\n", encoding="utf-8")
        monkeypatch.chdir(tmp_path)

        def fake_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
            calls.append(cmd)
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=0,
                stdout=b"tracked.py\0new_module.py\0",
                stderr=b"",
            )

        monkeypatch.setattr(subprocess, "run", fake_run)

        assert _find_modules() == ["tracked.py", "new_module.py"]
        assert calls == [["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"]]


class TestRunner:
    def test_unknown_check_name_exits_nonzero(self) -> None:
        # Fail-fast on a typo'd --only name (so a bad ci.yml reference is loud, not silent).
        with pytest.raises(SystemExit) as exc:
            run_selected("definitely-not-a-real-check")
        assert exc.value.code != 0

    def test_nonzero_step_exits_nonzero(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # A failing subprocess must propagate as sys.exit(1), not be swallowed.
        def fake_run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(args=args, returncode=1, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", fake_run)
        with pytest.raises(SystemExit) as exc:
            _run(["any-command"])
        assert exc.value.code != 0


class TestTrackedFilesCaptureFailure:
    """Broken `git ls-files` capture means unknown scope, not an empty list.

    This pins the **distinguishing** decision rather than mere validation: an
    empty list quietly reaches the secret gate, which prints "no files to scan —
    refusing to report a vacuous pass." The message has the right form but the
    **wrong cause**, sending the operator to investigate an empty repository
    instead of fixing capture.
    """

    def test_none_stdout_exits_two(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        def fake_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout=None, stderr=None)

        monkeypatch.setattr(subprocess, "run", fake_run)
        with pytest.raises(SystemExit) as exc:
            _tracked_files()
        assert exc.value.code == 2
        out = capsys.readouterr().out
        assert "file set is unknown" in out
        assert "no files to scan" not in out, "must not read as an empty repository"

    def test_git_failure_exits_two(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        def fake_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
            return subprocess.CompletedProcess(args=cmd, returncode=128, stdout=b"", stderr=b"")

        monkeypatch.setattr(subprocess, "run", fake_run)
        with pytest.raises(SystemExit) as exc:
            _tracked_files()

        assert exc.value.code == 2
        assert "git ls-files failed" in capsys.readouterr().out

    def test_mypy_manifest_none_stdout_exits_two(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        def fake_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout=None, stderr=None)

        monkeypatch.setattr(subprocess, "run", fake_run)
        with pytest.raises(SystemExit) as exc:
            _find_modules()

        assert exc.value.code == 2
        assert "file set is unknown" in capsys.readouterr().out

    def test_mypy_manifest_git_failure_exits_two(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        def fake_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
            return subprocess.CompletedProcess(args=cmd, returncode=128, stdout=b"", stderr=b"")

        monkeypatch.setattr(subprocess, "run", fake_run)
        with pytest.raises(SystemExit) as exc:
            _find_modules()

        assert exc.value.code == 2
        assert "git ls-files failed" in capsys.readouterr().out
