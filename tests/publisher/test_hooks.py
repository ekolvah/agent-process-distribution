"""Unit tests for the session-level PostToolUse hook (`scripts/hooks.py`).

The hook fires after every Edit/Write and dispatches two cheap checks in one
process: ruff (check-only) on `*.py`, and a pip-compile reminder on
`requirements*.in`. The deterministic decision logic lives in pure functions
(`plan_checks`, `classify_ruff_result`, `pipcompile_signal`, `exit_code`) so it
can be tested without spawning real ruff — the subprocess call is a thin I/O
wrapper (mirrors the `scripts/check_red.py` pure-function + thin-`main` split).

§IV note: a malformed/empty payload is a silent no-op (do not red every edit on
a payload bug), but a *ruff exec failure* (not installed / internal error) must
be a VISIBLE marker — otherwise the agent believes instant-lint is running when
it is not (a silent setup degradation).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.delivery_state import MAX_CONSECUTIVE_BLOCKS, fingerprint
from scripts.hooks import (
    _RUFF_EXEC_ERROR,
    _run_ruff,
    classify_ruff_result,
    exit_code,
    memory_write_signal,
    pipcompile_signal,
    plan_checks,
    run_on_edit,
    run_on_paths,
    stop_response,
)


def _payload(path: str | None) -> dict:
    if path is None:
        return {"tool_input": {}}
    return {"tool_input": {"file_path": path}}


class TestOnEditDispatch:
    def test_python_file_plans_ruff_check(self) -> None:
        assert plan_checks(_payload("src/kinozal_scraper/soldout_pipeline.py")) == ["ruff"]

    def test_non_python_skips_ruff(self) -> None:
        assert plan_checks(_payload(".agent-process/docs/architecture/ci.md")) == []
        assert plan_checks(_payload(".claude/settings.json")) == []

    def test_malformed_payload_silent_noop(self) -> None:
        # No file_path (and empty payload) → nothing planned, exit 0, no stderr.
        assert plan_checks(_payload(None)) == []
        assert plan_checks({}) == []
        code, stderr = run_on_edit({}, ruff_runner=_never_called)
        assert code == 0
        assert stderr == ""

    def test_run_on_edit_python_wires_dispatch_classify_exit(self) -> None:
        # End-to-end seam: a .py edit + a stubbed ruff run flows
        # plan_checks → ruff_runner → classify_ruff_result → exit_code as a whole.
        calls: list[str] = []

        def _stub(file_path: str) -> tuple[int, str]:
            calls.append(file_path)
            return 1, f"{file_path}:1:1: F401 unused import"

        code, stderr = run_on_edit(_payload("src/x.py"), ruff_runner=_stub)
        assert calls == ["src/x.py"]  # dispatch reached the runner with the edited path
        assert code == 2  # lint finding surfaces
        assert "F401" in stderr

    def test_run_on_edit_python_clean_is_silent(self) -> None:
        code, stderr = run_on_edit(_payload("src/x.py"), ruff_runner=lambda _f: (0, ""))
        assert code == 0
        assert stderr == ""

    def test_run_on_paths_deduplicates_multi_file_patch_paths(self) -> None:
        calls: list[str] = []

        def _stub(path: str) -> tuple[int, str]:
            calls.append(path)
            return 0, ""

        assert run_on_paths(["src/x.py", "src/x.py"], ruff_runner=_stub) == (0, "")
        assert calls == ["src/x.py"]


class TestRuffSignal:
    def test_lint_findings_surface_exit_2(self) -> None:
        # ruff returncode 1 = lint findings → visible marker, exit 2 (feedback to agent).
        sig = classify_ruff_result(1, "src/x.py:1:1: F401 unused import")
        assert sig is not None
        assert sig.kind == "lint"
        assert exit_code([sig]) == 2

    def test_ruff_exec_failure_is_visible_not_silent(self) -> None:
        # ruff returncode >=2 = ruff itself broke (bad config / not runnable).
        # Must be a VISIBLE, DISTINCT marker — not swallowed as "lint clean".
        sig = classify_ruff_result(2, "error: unknown option")
        assert sig is not None
        assert sig.kind == "setup_broken"
        assert sig.kind != "lint"
        assert exit_code([sig]) == 2

    def test_clean_returns_no_marker(self) -> None:
        assert classify_ruff_result(0, "") is None
        assert exit_code([]) == 0


class TestPipCompileGuard:
    def test_requirements_in_flagged(self) -> None:
        assert plan_checks(_payload("requirements.in")) == ["pipcompile"]
        assert plan_checks(_payload("requirements-dev.in")) == ["pipcompile"]
        sig = pipcompile_signal("requirements.in")
        assert "pip-compile" in sig.message
        assert exit_code([sig]) == 2

    def test_requirements_txt_ignored(self) -> None:
        # .txt is the generated lockfile, not the source — no reminder.
        assert plan_checks(_payload("requirements.txt")) == []
        assert plan_checks(_payload("requirements-dev.txt")) == []


class TestMemoryWriteGuard:
    """Writes to out-of-repo agent memory are a governance trigger.

    The Memory↔repo policy is enforced by a pure path predicate, like
    `_is_python`/`_is_requirements_in`. It emits a checkpoint reminder (exit 2),
    not a PreToolUse block; machine-specific-memory false positives are accepted
    by design because semantics are not scripted.
    """

    _MEM = (
        "C:/Users/jadow/.claude/projects/"
        "C--Users-jadow-PycharmProjects-kinozal-scraper/memory/some_fact.md"
    )

    def test_memory_path_flags_memory_write(self) -> None:
        assert plan_checks(_payload(self._MEM)) == ["memory_write"]

    def test_memory_write_surfaces_exit_2(self) -> None:
        # The signal is a visible anomaly (§IV): exit 2 exposes stderr to the
        # agent. The memory branch precedes `_is_python`, so ruff never runs.
        code, stderr = run_on_edit(_payload(self._MEM), ruff_runner=_never_called)
        assert code == 2
        assert stderr != ""
        sig = memory_write_signal(self._MEM)
        assert sig.kind == "memory_write"

    def test_windows_backslash_path(self) -> None:
        # Windows payloads can contain backslashes; normalize them.
        p = r"C:\Users\jadow\.claude\projects\slug\memory\bar.md"
        assert plan_checks(_payload(p)) == ["memory_write"]

    def test_memory_index_root_file_flagged(self) -> None:
        # A trailing slash must not exclude MEMORY.md at the memory root.
        p = "C:/Users/jadow/.claude/projects/slug/memory/MEMORY.md"
        assert plan_checks(_payload(p)) == ["memory_write"]

    def test_non_memory_subdir_of_projects_not_flagged(self) -> None:
        # Match `/memory/`, not all `projects/`, which also stores session logs.
        p = "C:/Users/jadow/.claude/projects/slug/other/f.md"
        assert plan_checks(_payload(p)) == []

    def test_repo_paths_not_memory(self) -> None:
        # Repository files, including `.claude/`, do not trigger the memory signal.
        assert plan_checks(_payload("src/x.py")) == ["ruff"]
        assert plan_checks(_payload(".agent-process/docs/architecture/project-map.md")) == []
        assert plan_checks(_payload(".claude/rules/mindset.md")) == []


def _never_called(_file: str) -> tuple[int, str]:
    raise AssertionError("ruff_runner must not run when nothing is planned")


class TestCaptureFailureIsSetupBroken:
    """Broken ruff output capture means setup failure, not an exception.

    An uncaught exception would return hook exit 1, whose stderr reaches the user
    but not the agent; the agent sees exit 2. A visibility tool must remain visible
    when it breaks. This shares the missing-ruff class: the check did not run,
    rather than findings being present.
    """

    def test_none_stdout_returns_setup_broken_marker(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def fake_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout=None, stderr=None)

        monkeypatch.setattr(subprocess, "run", fake_run)
        returncode, output = _run_ruff("some_file.py")
        assert returncode == _RUFF_EXEC_ERROR
        assert "capture failed" in output


_BRANCH = "issue-56-bug-keep-delivery-active"
_HEAD = "a54549ac1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e"  # pragma: allowlist secret


def _git_runner(branch: str, head: str, *, dirty: bool = False) -> tuple[list[list[str]], object]:
    """A `subprocess.run` double answering only the three local git reads
    `stop_response` is allowed to make — no `ci_check.py`, `gh`, or
    `review_gate.py` launch, ever (AC 4)."""
    calls: list[list[str]] = []

    def runner(args: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        if args == ["git", "branch", "--show-current"]:
            return subprocess.CompletedProcess(args, 0, stdout=f"{branch}\n", stderr="")
        if args == ["git", "rev-parse", "HEAD"]:
            return subprocess.CompletedProcess(args, 0, stdout=f"{head}\n", stderr="")
        if args == ["git", "status", "--porcelain"]:
            stdout = " M dirty-file.py\n" if dirty else ""
            return subprocess.CompletedProcess(args, 0, stdout=stdout, stderr="")
        raise AssertionError(f"stop_response must not launch: {args}")

    return calls, runner


class TestStopHook:
    """The Claude `Stop` adapter: blocks the turn from ending while a delivery
    on an `issue-*` branch has not reached a terminal review-gate verdict."""

    def test_non_terminal_delivery_blocks_with_a_reason(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _calls, runner = _git_runner(_BRANCH, _HEAD)

        response = stop_response({}, runner=runner)

        assert response is not None
        assert response["decision"] == "block"
        assert "reason" in response

    def test_terminal_delivery_returns_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".ci_check_stamp").write_text(_HEAD, encoding="utf-8")
        (tmp_path / ".review_gate_stamp").write_text(f"{_HEAD} ready-for-human", encoding="utf-8")
        _calls, runner = _git_runner(_BRANCH, _HEAD)

        assert stop_response({}, runner=runner) is None

    def test_non_delivery_branch_returns_none_without_reading_stamps(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _calls, runner = _git_runner("main", _HEAD)

        assert stop_response({}, runner=runner) is None

    def test_budget_exhaustion_yields_a_system_message_with_no_decision_key(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        fp = fingerprint(_BRANCH, _HEAD, None, None)
        (tmp_path / ".agent_stop_blocks").write_text(
            f"{fp} {MAX_CONSECUTIVE_BLOCKS}", encoding="utf-8"
        )
        _calls, runner = _git_runner(_BRANCH, _HEAD)

        response = stop_response({}, runner=runner)

        assert response is not None
        assert "decision" not in response
        assert "systemMessage" in response

    def test_in_flight_ci_state_blocks_and_launches_no_ci_process(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`.ci_check_stamp` absent on an issue branch — blocks, and the
        injected runner proves the hook read state rather than re-running it:
        exactly the three git reads, nothing else."""
        monkeypatch.chdir(tmp_path)
        calls, runner = _git_runner(_BRANCH, _HEAD)

        response = stop_response({}, runner=runner)

        assert response is not None
        assert response["decision"] == "block"
        assert calls == [
            ["git", "branch", "--show-current"],
            ["git", "rev-parse", "HEAD"],
            ["git", "status", "--porcelain"],
        ]

    def test_dirty_worktree_blocks_even_on_a_terminal_verdict(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Terminal stamps say nothing about changes made after they were
        written — an uncommitted edit must not let the turn end silently
        (agent-review finding on #56)."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".ci_check_stamp").write_text(_HEAD, encoding="utf-8")
        (tmp_path / ".review_gate_stamp").write_text(f"{_HEAD} ready-for-human", encoding="utf-8")
        _calls, runner = _git_runner(_BRANCH, _HEAD, dirty=True)

        response = stop_response({}, runner=runner)

        assert response is not None
        assert response["decision"] == "block"
        assert "uncommitted" in response["reason"]

    def test_unreadable_git_state_fails_closed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)

        def broken_runner(_args: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(_args, returncode=1, stdout="", stderr="fatal")

        response = stop_response({}, runner=broken_runner)

        assert response is not None
        assert response["decision"] == "block"

    def test_detached_head_is_an_inert_allow_not_unreadable(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`git branch --show-current` exits 0 with empty stdout in detached HEAD
        — a normal, non-error git state, not a failed read. It must read as "not
        a delivery branch" (allow), not `unreadable_state_decision` (agent-review
        finding on #56)."""
        monkeypatch.chdir(tmp_path)

        def runner(args: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
            if args == ["git", "branch", "--show-current"]:
                return subprocess.CompletedProcess(args, 0, stdout="", stderr="")
            if args == ["git", "rev-parse", "HEAD"]:
                return subprocess.CompletedProcess(args, 0, stdout=f"{_HEAD}\n", stderr="")
            if args == ["git", "status", "--porcelain"]:
                return subprocess.CompletedProcess(args, 0, stdout="", stderr="")
            raise AssertionError(f"stop_response must not launch: {args}")

        assert stop_response({}, runner=runner) is None


def test_pre_read_is_an_accepted_subcommand() -> None:
    """`main()` is fail-CLOSED on an unknown argv (exit 2). Behind a `Read` matcher that
    reads as "deny every Read in the session" — the opposite of the fail-open policy — so
    the dispatcher's allowlist is a guarded requirement, not an implementation detail.
    """
    result = subprocess.run(
        [sys.executable, ".agent-process/scripts/hooks.py", "pre-read"],
        input="{}",
        capture_output=True,
        encoding="utf-8",
        cwd=Path(__file__).resolve().parents[2],
        env={**os.environ, "PYTHONUTF8": "1"},
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == ""
