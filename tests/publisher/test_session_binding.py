"""``session_binding`` and its three callers: one Claude Code session leads one task
(change session-task-attribution).

The ledger is `<git common dir>/agent-process/sessions`; the fake `gh` answers the common dir
as `<root>/.git`. Scripts are imported inside the tests, as in ``test_start_change``.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from tests.publisher.delivery_fakes import (
    CHANGE,
    GROUP0,
    ISSUE,
    PLACEHOLDER,
    START,
    TOKEN,
    Gh,
    creates,
    develops,
    load_script,
    make_change,
)

_VARIABLE = "CLAUDE_CODE_SESSION_ID"
_OTHER = ISSUE - 2
_AREA = [CHANGE, "--area", "Observability"]


def _ledger(root: Path) -> Path:
    return root / ".git" / "agent-process" / "sessions"


def _seed(root: Path, text: str) -> None:
    ledger = _ledger(root)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text(text, encoding="utf-8")


def _archive_run(main: Path, worktree: Path) -> Callable[[list[str]], str]:
    """`archive_change`'s runner in a worktree of `main`: a clean status, `openspec archive`
    moves the change under the archive, and the rest succeeds."""

    def run(cmd: list[str]) -> str:
        if cmd[-3:] == ["rev-parse", "--path-format=absolute", "--git-common-dir"]:
            return f"{main / '.git'}\n"
        if cmd[:2] == ["git", "status"]:
            return ""
        if cmd[0] == "npx":
            changes = worktree / "openspec" / "changes"
            (changes / "archive").mkdir(exist_ok=True)
            (changes / CHANGE).rename(changes / "archive" / f"2026-01-01-{CHANGE}")
            return ""
        if cmd[:2] in (["git", "add"], ["git", "commit"], ["git", "push"]):
            return ""
        raise AssertionError(f"unexpected call: {cmd}")

    return run


def test_second_task_in_one_session(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Scenario: Second task in one session — exit 2 naming both issues, no branch."""
    start_change = load_script("start_change")
    root = make_change(tmp_path, tasks=GROUP0.format(token=TOKEN))
    _seed(root, f"s-1 {_OTHER}\n")
    monkeypatch.setenv(_VARIABLE, "s-1")
    gh = Gh(status="Planned", root=root)

    with pytest.raises(SystemExit) as exc:
        start_change.main(START, gh=gh, root=root)

    assert exc.value.code == 2
    assert develops(gh) == []
    err = capsys.readouterr().err
    assert f"issue-{_OTHER}" in err and f"issue-{ISSUE}" in err
    assert "new session" in err


def test_plan_creates_the_issue(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Scenario: Plan creates the issue — the session is bound to the created issue."""
    create = load_script("finish_propose")
    root = make_change(tmp_path, tasks=GROUP0.format(token=PLACEHOLDER))
    monkeypatch.setenv(_VARIABLE, "s-plan")

    create.main(_AREA, gh=Gh(root=root), root=root)

    assert _ledger(root).read_text(encoding="utf-8").splitlines() == [f"s-plan {ISSUE}"]


def test_no_session_variable(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Scenario: No session variable — `session not bound` is printed and the change starts."""
    start_change = load_script("start_change")
    root = make_change(tmp_path, tasks=GROUP0.format(token=TOKEN))
    gh = Gh(status="Planned", root=root)

    start_change.main(START, gh=gh, root=root)

    assert "session not bound" in capsys.readouterr().out
    assert len(develops(gh)) == 1
    assert not _ledger(root).exists()


def test_plan_and_implementation_in_two_sessions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Scenario: Plan and implementation in two sessions — the archived `sessions` lists both."""
    create = load_script("finish_propose")
    start_change = load_script("start_change")
    archive_change = load_script("archive_change")
    root = make_change(tmp_path, tasks=GROUP0.format(token=PLACEHOLDER))
    monkeypatch.setenv(_VARIABLE, "s-plan")
    create.main(_AREA, gh=Gh(root=root), root=root)
    monkeypatch.setenv(_VARIABLE, "s-impl")
    start_change.main(START, gh=Gh(status="Planned", root=root), root=root)
    worktree = root / ".claude" / "worktrees" / CHANGE

    code = archive_change.archive_change(CHANGE, root=worktree, run=_archive_run(root, worktree))

    assert code == 0
    archived = worktree / "openspec" / "changes" / "archive" / f"2026-01-01-{CHANGE}"
    assert (archived / "sessions").read_text(encoding="utf-8") == "s-impl\ns-plan\n"


def test_same_issue_binds_once(tmp_path: Path) -> None:
    """D2: a second `bind` of the same issue leaves one ledger line."""
    binding = load_script("session_binding")
    ledger = tmp_path / "agent-process" / "sessions"
    environ = {_VARIABLE: "s-1"}

    binding.bind(ISSUE, environ=environ, ledger=lambda: ledger)
    binding.bind(ISSUE, environ=environ, ledger=lambda: ledger)

    assert ledger.read_text(encoding="utf-8").splitlines() == [f"s-1 {ISSUE}"]
    assert binding.sessions(ISSUE, ledger=ledger) == ["s-1"]


def test_side_issue_refused_before_create(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """D3: a session bound to another issue cannot create a change's issue."""
    create = load_script("finish_propose")
    root = make_change(tmp_path, tasks=GROUP0.format(token=PLACEHOLDER))
    _seed(root, f"s-1 {_OTHER}\n")
    monkeypatch.setenv(_VARIABLE, "s-1")
    gh = Gh(root=root)

    with pytest.raises(SystemExit) as exc:
        create.main(_AREA, gh=gh, root=root)

    assert exc.value.code == 2
    assert creates(gh) == []
    assert f"issue-{_OTHER}" in capsys.readouterr().err


def test_rerun_after_failed_archive(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """D4: the `sessions` file a failed `openspec archive` left passes the clean-worktree
    check of the re-run, which rewrites it."""
    archive_change = load_script("archive_change")
    real = archive_change._runner(tmp_path)
    failures = [RuntimeError("`npx … archive` failed (rc=1): boom")]

    def run(cmd: list[str]) -> str:
        if cmd[0] == "npx":
            if failures:
                raise failures.pop()
            changes = tmp_path / "openspec" / "changes"
            (changes / CHANGE).rename(changes / "archive" / f"2026-01-01-{CHANGE}")
            return ""
        if cmd[:2] == ["git", "push"]:
            return ""
        return real(cmd)

    for args in (["init", "-q", "-b", CHANGE], ["config", "user.name", "t"]):
        real(["git", *args])
    real(["git", "config", "user.email", "t@t"])
    tasks = tmp_path / "openspec" / "changes" / CHANGE / "tasks.md"
    tasks.parent.mkdir(parents=True)
    (tmp_path / "openspec" / "changes" / "archive").mkdir()
    tasks.write_text(GROUP0.format(token=TOKEN), encoding="utf-8")
    real(["git", "add", "-A"])
    real(["git", "commit", "-qm", "plan"])
    monkeypatch.setenv(_VARIABLE, "s-1")

    with pytest.raises(RuntimeError, match="boom"):
        archive_change.archive_change(CHANGE, root=tmp_path, run=run)
    assert (tasks.parent / "sessions").read_text(encoding="utf-8") == "s-1\n"
    with _ledger(tmp_path).open("a", encoding="utf-8") as f:
        f.write(f"s-2 {ISSUE}\n")

    assert archive_change.archive_change(CHANGE, root=tmp_path, run=run) == 0
    archived = tmp_path / "openspec" / "changes" / "archive" / f"2026-01-01-{CHANGE}"
    assert (archived / "sessions").read_text(encoding="utf-8") == "s-1\ns-2\n"
    assert real(["git", "status", "--porcelain"]) == ""
