"""``wait_for_pr`` and ``archive_change``, the PR end of the OpenSpec delivery loop (changes
v2-1a-delivery-scripts and v2-2e-wait-for-pr-checks).

One test per scenario of the change's spec deltas that a script can prove; the
scenario name is the test name. Scripts are imported inside the tests so that a
missing script fails its own scenario instead of erroring the whole module at
collection (``check_red`` counts a collection error as "not RED").
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from tests.publisher.delivery_fakes import load_script


def _checks(*checks: tuple[str, str]) -> tuple[int, str, str]:
    """A `gh pr checks --json name,bucket,link` read: exit 0 whatever the buckets are."""
    rows = [{"name": n, "bucket": b, "link": f"https://ci.test/{n}"} for n, b in checks]
    return 0, json.dumps(rows), ""


# The rollup is empty for seconds after a push: gh reports it as an error, not as `[]`.
_EMPTY = (1, "", "no checks reported on the 'x' branch\n")
_PR_URL = "https://github.com/owner/repo/pull/9"


def _threads(*unresolved: str, head: str = "A") -> str:
    return json.dumps(
        {
            "data": {
                "repository": {
                    "pullRequest": {
                        "url": _PR_URL,
                        "headRefOid": head,
                        "reviewThreads": {
                            "pageInfo": {"hasNextPage": False},
                            "nodes": [
                                {
                                    "id": f"T_{i}",
                                    "isResolved": False,
                                    "path": path,
                                    "line": 1,
                                    "comments": {
                                        "nodes": [
                                            {
                                                "author": {"login": "reviewer"},
                                                "body": f"fix {path}",
                                                "url": f"https://github.com/t/{i}",
                                            }
                                        ]
                                    },
                                }
                                for i, path in enumerate(unresolved)
                            ],
                        },
                    }
                }
            }
        }
    )


_QUALITY, _REVIEW = "agent-process / quality", "agent-review / agent-review"


def _status_rule(*contexts: str) -> dict[str, Any]:
    checks = [{"context": c, "integration_id": 15368} for c in contexts]
    return {
        "type": "required_status_checks",
        "parameters": {
            "do_not_enforce_on_create": False,
            "required_status_checks": checks,
            "strict_required_status_checks_policy": False,
        },
    }


def _rules(*required: str, extra_rule: bool = False) -> tuple[int, str, str]:
    """A `gh api …/rules/branches/main` read as observed in this repository: a `pull_request`
    rule, a `required_status_checks` rule of `required` and, with `extra_rule`, a second one
    of `pr-title`; `[]` with neither."""
    rules: list[dict[str, Any]] = []
    if required:
        rules += [{"type": "pull_request", "parameters": {}}, _status_rule(*required)]
    if extra_rule:
        rules.append(_status_rule("pr-title"))
    return 0, json.dumps(rules), ""


class _Sequence:
    """Fake `gh` for `wait_for_pr`, a `CompletedProcess` per call: for `gh pr checks … --json`
    the next of the `(rc, stdout, stderr)` reads (the last one repeats), counted in `polls`;
    for `gh pr view … --json headRefOid` the next of `heads`, for `baseRefName` `main`; for
    the rules of `main` the `rules` read; for the GraphQL query the next of the threads
    payloads (the last ones repeat)."""

    def __init__(
        self,
        reads: list[tuple[int, str, str]],
        threads: str | list[str],
        heads: list[str] | None = None,
        rules: tuple[int, str, str] = _rules(_QUALITY, _REVIEW),
    ) -> None:
        self.reads = list(reads)
        self.threads = [threads] if isinstance(threads, str) else list(threads)
        self.heads = list(heads or ["A"])
        self.rules = rules
        self.polls = 0

    @staticmethod
    def _next(items: list[Any]) -> Any:
        return items.pop(0) if len(items) > 1 else items[0]

    def __call__(self, cmd: list[str]) -> subprocess.CompletedProcess[str]:
        if cmd[:3] == ["gh", "pr", "checks"]:
            assert "--json" in cmd and "--watch" not in cmd, cmd
            self.polls += 1
            rc, out, err = self._next(self.reads)
            return subprocess.CompletedProcess(cmd, rc, out, err)
        if cmd[:3] == ["gh", "pr", "view"]:
            if "baseRefName" in cmd:
                view = {"baseRefName": "main"}
            else:
                assert "headRefOid" in cmd, cmd
                view = {"headRefOid": self._next(self.heads)}
            return subprocess.CompletedProcess(cmd, 0, json.dumps(view), "")
        if cmd[:3] == ["gh", "repo", "view"]:
            repo = json.dumps({"owner": {"login": "owner"}, "name": "repo"})
            return subprocess.CompletedProcess(cmd, 0, repo, "")
        if cmd[:3] == ["gh", "api", "graphql"]:
            return subprocess.CompletedProcess(cmd, 0, self._next(self.threads), "")
        if cmd[:3] == ["gh", "api", "repos/{owner}/{repo}/rules/branches/main"]:
            return subprocess.CompletedProcess(cmd, *self.rules)
        raise AssertionError(f"unexpected gh call: {cmd}")


def _wait(
    capsys: pytest.CaptureFixture[str],
    reads: list[tuple[int, str, str]],
    threads: str | list[str] = _threads(),
    *,
    timeout: int = 1800,
    **fake: Any,
) -> tuple[int, str, _Sequence, list[float]]:
    """Run `wait_for_pr` on the fake `gh` (`fake`: its `heads`, `rules`); the fake `sleep`
    advances the fake `clock`."""
    wait_for_pr = load_script("wait_for_pr")
    gh = _Sequence(reads, threads, **fake)
    now = [0.0]
    sleeps: list[float] = []

    def sleep(seconds: float) -> None:
        sleeps.append(seconds)
        now[0] += seconds

    code = wait_for_pr.wait_for_pr(9, gh=gh, clock=lambda: now[0], sleep=sleep, timeout=timeout)
    return code, capsys.readouterr().out, gh, sleeps


def test_pending_review(capsys: pytest.CaptureFixture[str]) -> None:
    """Scenario: Pending review — a `pending` bucket is a pending review; `fail`, `cancel` or
    an unresolved thread → 1; clean → 0; timeout → 3 naming the check; a `gh` failure is an
    error, never a verdict."""
    wait_for_pr = load_script("wait_for_pr")
    green, running = (_QUALITY, "pass"), (_REVIEW, "pending")
    red, cancelled, done = ((_REVIEW, "fail"), (_REVIEW, "cancel"), (_REVIEW, "pass"))
    # The two-read cases below hold where the fast check alone is all the base requires.
    only_quality = _rules(_QUALITY)

    code, out, gh, _ = _wait(capsys, [_checks(green, running), _checks(green, red)])
    assert code == 1 and "failed: agent-review" in out and gh.polls == 3

    code, out, _, _ = _wait(capsys, [_checks(green, cancelled)])
    assert code == 1 and "failed: agent-review" in out

    code, out, _, _ = _wait(capsys, [_checks(green, done)], _threads("docs/a.md"))
    assert code == 1 and "docs/a.md" in out

    code, out, gh, sleeps = _wait(capsys, [_checks(green, done)])
    assert code == 0 and "clean:" in out and _PR_URL in out
    # A concluded set is trusted once two reads 30 s apart agree on it: a workflow that
    # attaches late is never hidden behind a fast one that already passed, because a clean
    # verdict ends the delivery loop and no later read would see it (PR 147, round 2).
    assert gh.polls == 2 and sleeps == [30]
    code, out, gh, _ = _wait(
        capsys,
        [_checks(green), _checks(green, running), _checks(green, done)],
        rules=only_quality,
    )
    assert code == 0 and gh.polls == 4
    # The two reads must be of one head (PR 147, round 3): a push between them, each head
    # read while only its fast check had attached, agrees on the names and proves nothing.
    code, out, gh, _ = _wait(
        capsys,
        [_checks(green), _checks(green), _checks(green, running), _checks(green, done)],
        _threads(head="B"),
        heads=["A", "B"],
        rules=only_quality,
    )
    assert code == 0 and gh.polls == 5
    # A push after the last read: the threads answer names another head → read again on it.
    code, out, gh, _ = _wait(
        capsys, [_checks(green, done)], _threads(head="B"), heads=["A", "A", "B"]
    )
    assert code == 0 and gh.polls == 4 and "waiting: a push" in out

    code, out, _, sleeps = _wait(capsys, [_checks(green, running)], timeout=120)
    assert code == 3 and "timeout" in out.lower() and "agent-review" in out
    assert sleeps == [30, 30, 30, 30]

    # The timeout is the time that elapsed, not the number of whole poll intervals that fit
    # (PR 147, round 1): a timeout that is not a multiple of the interval is waited through,
    # the last sleep is the remainder, and the last read is at the deadline.
    code, out, gh, sleeps = _wait(capsys, [_checks(green, running)], timeout=31)
    assert code == 3 and sleeps == [30, 1] and gh.polls == 3
    code, out, gh, sleeps = _wait(capsys, [_checks(green, running)], timeout=10)
    assert code == 3 and sleeps == [10] and gh.polls == 2

    with pytest.raises(RuntimeError, match="401"):
        wait_for_pr.wait_for_pr(
            9,
            gh=_Sequence([(1, "", "HTTP 401")], _threads()),
            clock=lambda: 0.0,
            sleep=lambda s: None,
        )


def test_empty_rollup_after_push(capsys: pytest.CaptureFixture[str]) -> None:
    """Scenario: Empty rollup after a push — `no checks reported` is read again after one
    poll interval, never reported clean or failed; a rollup that never fills → 3."""
    green, done = (_QUALITY, "pass"), (_REVIEW, "pass")

    code, out, gh, sleeps = _wait(capsys, [_EMPTY, _checks(green, done)])
    assert code == 0 and sleeps == [30, 30] and gh.polls == 3

    code, out, _, _ = _wait(capsys, [_EMPTY], timeout=120)
    assert code == 3 and "no checks" in out.lower()


def test_required_check_not_yet_attached(capsys: pytest.CaptureFixture[str]) -> None:
    """Scenario: Required check not yet attached — a head reporting only concluded foreign
    checks is waited on, never clean; the timeout names each required check it lacks, of
    every rule; a failed read of the rules is an error, never a verdict (issue 348)."""
    wait_for_pr = load_script("wait_for_pr")
    foreign = (("CodeQL", "pass"), ("Analyze (python)", "pass"))
    quality, review = (_QUALITY, "pass"), (_REVIEW, "pass")

    code, out, _, _ = _wait(capsys, [_checks(*foreign)], timeout=120)
    assert code == 3 and "clean:" not in out
    assert _QUALITY in out and _REVIEW in out and "(not reported)" in out

    code, out, _, _ = _wait(capsys, [_checks(*foreign, quality)], timeout=120)
    timeout_line = out.splitlines()[-1]
    assert code == 3 and timeout_line.startswith("timeout")
    assert _REVIEW in timeout_line and _QUALITY not in timeout_line

    code, out, gh, _ = _wait(capsys, [_checks(*foreign), _checks(*foreign, quality, review)])
    assert code == 0 and "clean:" in out and gh.polls == 3

    code, out, _, _ = _wait(
        capsys,
        [_checks(*foreign, quality, review)],
        timeout=120,
        rules=_rules(_QUALITY, _REVIEW, extra_rule=True),
    )
    timeout_line = out.splitlines()[-1]
    assert code == 3 and "pr-title" in timeout_line
    assert _QUALITY not in timeout_line and _REVIEW not in timeout_line

    with pytest.raises(RuntimeError, match="HTTP 404"):
        wait_for_pr.wait_for_pr(
            9,
            gh=_Sequence(
                [_checks(quality, review)], _threads(), rules=(1, "", "HTTP 404: Not Found")
            ),
            clock=lambda: 0.0,
            sleep=lambda s: None,
        )


def test_no_required_checks_on_the_base_branch(capsys: pytest.CaptureFixture[str]) -> None:
    """Scenario: No required checks on the base branch — a note says the wait settles on the
    reported checks only, then the head is waited on as any other."""
    code, out, _, _ = _wait(capsys, [_checks(("lint", "pass"))], rules=_rules())
    assert code == 0 and "clean:" in out
    assert out.splitlines()[0].startswith("note: main requires no status check")


@pytest.mark.parametrize(
    ("script", "attr"),
    [("set_status", "run_gh"), ("wait_for_pr", "run_gh"), ("archive_change", "_runner")],
)
def test_none_capture_is_an_error(monkeypatch: pytest.MonkeyPatch, script: str, attr: str) -> None:
    """CLAUDE.md: a `None` stdout or stderr is a broken capture, never an empty string."""
    module = load_script(script)

    class _Completed:
        returncode = 0
        stdout = None
        stderr = None

    monkeypatch.setattr(module.subprocess, "run", lambda *a, **k: _Completed())
    runner = getattr(module, attr)
    if attr == "_runner":
        runner = runner(Path("."))
    with pytest.raises(RuntimeError, match="capture"):
        runner(["gh", "repo", "view"])


def test_archive_runner_reports_a_failed_command_whose_output_is_not_utf8() -> None:
    """A pre-push hook that writes a code-page byte still reaches the operator: the
    failure names the command and its output, not a broken capture (§IV)."""
    runner = load_script("archive_change")._runner(Path("."))
    child = "import sys; sys.stderr.buffer.write(b'tests failed \\x97 see above\\n'); sys.exit(1)"

    with pytest.raises(RuntimeError, match=r"failed \(rc=1\).*tests failed"):
        runner([sys.executable, "-c", child])


@pytest.mark.parametrize(
    "own_task",
    [
        "python skills/agent-process/scripts/archive_change.py {change}",
        "agent-process archive_change {change}",
    ],
    ids=["python", "agent-process"],
)
def test_archive_commit(tmp_path: Path, own_task: str) -> None:
    """Scenarios: Archive commit, Stale archive lock; either command form ticks the own task."""
    archive_change = load_script("archive_change")
    change = "v2-9-example"
    change_dir = tmp_path / "openspec" / "changes" / change
    change_dir.mkdir(parents=True)
    archive = tmp_path / "openspec" / "changes" / "archive"
    archive.mkdir()
    lock = archive / ".openspec-archive.lock"
    tasks = change_dir / "tasks.md"
    # The own task's command sits on a continuation line (as on #124's task 4.3).
    tasks.write_text(
        "- [x] 1.1 done\n"
        "- [ ] 4.1 `git status --short` empty;\n"
        f"  `{own_task.format(change=change)}` archives, commits, pushes.\n"
        "- [ ] 4.2 `gh pr create`; the person merges.\n",
        encoding="utf-8",
    )
    order: list[str] = []
    status = ""

    def run(cmd: list[str]) -> str:
        if "archive" in cmd:
            order.append("archive")
            text = tasks.read_text(encoding="utf-8")
            assert "- [x] 4.1" in text and "- [ ] 4.2" in text
            (archive / f"2026-01-01-{change}").mkdir()
            tasks.replace(archive / f"2026-01-01-{change}" / "tasks.md")
            lock.write_text("", encoding="utf-8")
            return ""
        if cmd[:2] == ["git", "commit"]:
            order.append("commit")
            assert not lock.exists()
            return ""
        if cmd[:2] == ["git", "push"]:
            order.append("push")
            return ""
        if cmd[:2] == ["git", "add"]:
            return ""
        if cmd[:2] == ["git", "status"]:
            return status
        raise AssertionError(f"unexpected call: {cmd}")

    # No review request and no wait: the PR does not exist yet when the archive lands.
    assert archive_change.archive_change(change, root=tmp_path, run=run) == 0
    assert order == ["archive", "commit", "push"]

    # Scenario: Stale archive lock — a lock left by an interrupted run stops the script.
    lock.write_text("", encoding="utf-8")
    order.clear()
    assert archive_change.archive_change(change, root=tmp_path, run=run) == 2
    assert order == []

    # Scenario: Archive commit — the worktree must be clean before the archive; a stray edit
    # would be left behind the pushed head, so the script stops instead of committing openspec/.
    lock.unlink()
    status = " M skills/agent-process/scripts/wait_for_pr.py\n"
    assert archive_change.archive_change(change, root=tmp_path, run=run) == 2
    assert order == []


def test_ticks_left_for_the_archive(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Scenario: Ticks left for the archive — a modified own `tasks.md` rides in the archive
    commit; another changed file, or that `tasks.md` deleted, still stops it (issue 252)."""
    archive_change = load_script("archive_change")
    change = "v2-9-example"
    rel = f"openspec/changes/{change}/tasks.md"
    real = archive_change._runner(tmp_path)

    def git(*args: str) -> str:
        return real(["git", *args])

    def run(cmd: list[str]) -> str:
        if cmd[0] == "npx":  # `openspec archive` moves the change under the archive
            (tmp_path / "openspec" / "changes" / change).rename(
                tmp_path / "openspec" / "changes" / "archive" / f"2026-01-01-{change}"
            )
            return ""
        if cmd[:2] == ["git", "push"]:
            return ""
        return real(cmd)

    git("init", "-q", "-b", change)
    git("config", "user.name", "t")
    git("config", "user.email", "t@t")
    tasks = tmp_path / rel
    tasks.parent.mkdir(parents=True)
    (tmp_path / "openspec" / "changes" / "archive").mkdir()
    tasks.write_text("- [ ] 4.1 verify\n- [ ] 5.1 `archive_change.py v2-9-example`\n", "utf-8")
    (tmp_path / "other.txt").write_text("a\n", encoding="utf-8")
    git("add", "-A")
    git("commit", "-qm", "plan")
    base = git("rev-parse", "HEAD")

    # Another changed file beside the ticks: exit 2, the file named, nothing committed.
    tasks.write_text("- [x] 4.1 verify\n- [ ] 5.1 `archive_change.py v2-9-example`\n", "utf-8")
    (tmp_path / "other.txt").write_text("b\n", encoding="utf-8")
    assert archive_change.archive_change(change, root=tmp_path, run=run) == 2
    assert "other.txt" in capsys.readouterr().err
    assert git("rev-parse", "HEAD") == base

    # The own `tasks.md` deleted: exit 2, it is named, nothing committed.
    git("checkout", "-q", "--", ".")
    tasks.unlink()
    assert archive_change.archive_change(change, root=tmp_path, run=run) == 2
    assert rel in capsys.readouterr().err
    assert git("rev-parse", "HEAD") == base

    # Only the ticks: the archive commit carries them and the worktree is clean.
    git("checkout", "-q", "--", ".")
    tasks.write_text("- [x] 4.1 verify\n- [ ] 5.1 `archive_change.py v2-9-example`\n", "utf-8")
    assert archive_change.archive_change(change, root=tmp_path, run=run) == 0
    assert git("status", "--porcelain") == ""
    archived = git("show", f"HEAD:openspec/changes/archive/2026-01-01-{change}/tasks.md")
    assert archived.splitlines() == [
        "- [x] 4.1 verify",
        "- [x] 5.1 `archive_change.py v2-9-example`",
    ]
