#!/usr/bin/env python3
"""Close a change inside its PR: archive, commit, push, re-request the review, wait.

Usage: python .agent-process/scripts/finish_change.py <change>

The last task of every `tasks.md`. `openspec archive` moves `tasks.md` into the archive, so
nothing can mark this task after it ran: the script marks its own box first, then archives,
removes the lock a successful archive leaves behind, commits, pushes, re-requests the Codex
review when `request_codex_review.py` is present (the `agent-review` check binds to the
head, so every push needs a new request; says so when the script is absent) and runs
`wait_for_pr` on the new head. Exit codes: 0 clean; the `wait_for_pr` code otherwise;
2 when the worktree is not clean (the archive commit must be the only thing left to push)
or when `openspec/changes/archive/.openspec-archive.lock` already exists — a previous
archive aborted and its state must be inspected before anything is archived on top of it.
The person merges.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

try:
    from scripts.wait_for_pr import wait_for_pr
except ModuleNotFoundError:  # documented direct script entry point
    from wait_for_pr import wait_for_pr

Run = Callable[[list[str]], str]
LOCK = Path("openspec", "changes", "archive", ".openspec-archive.lock")
REVIEW_REQUEST = Path(".agent-process", "scripts", "request_codex_review.py")


def _runner(root: Path) -> Run:
    def run(cmd: list[str]) -> str:
        exe = shutil.which(cmd[0]) or cmd[0]
        result = subprocess.run(
            [exe, *cmd[1:]], cwd=root, text=True, capture_output=True, encoding="utf-8"
        )
        if result.stdout is None or result.stderr is None:
            raise RuntimeError(f"`{' '.join(cmd)}`: broken capture (stdout or stderr is None)")
        if result.returncode != 0:
            detail = (result.stderr or result.stdout).strip() or "no output"
            raise RuntimeError(f"`{' '.join(cmd)}` failed (rc={result.returncode}): {detail}")
        return result.stdout

    return run


def _mark_own_task(tasks: Path, change: str) -> None:
    """Tick the `finish_change.py <change>` task; a missing line is reported, not fatal."""
    text = tasks.read_text(encoding="utf-8")
    pattern = re.compile(rf"^- \[ \] (?=.*finish_change\.py {re.escape(change)}\b)", re.M)
    text, count = pattern.subn("- [x] ", text, count=1)
    if count:
        tasks.write_text(text, encoding="utf-8")
    else:
        print(f"note: no unchecked `finish_change.py {change}` task in {tasks}; nothing marked")


def _pr_number(run: Run) -> int:
    data = json.loads(run(["gh", "pr", "view", "--json", "number"]))
    return int(data["number"])


def finish_change(
    change: str,
    *,
    root: Path = Path("."),
    run: Run | None = None,
    wait: Callable[[int], int] = wait_for_pr,
) -> int:
    run = run or _runner(root)
    lock = root / LOCK
    if lock.exists():
        print(
            f"error: {lock} exists — a previous archive aborted; inspect "
            f"openspec/changes/archive/ and remove the lock by hand before archiving",
            file=sys.stderr,
        )
        return 2
    dirty = run(["git", "status", "--porcelain"]).strip()
    if dirty:
        print(
            "error: the worktree is not clean — commit or drop these before archiving, or "
            f"the pushed head would not carry them:\n{dirty}",
            file=sys.stderr,
        )
        return 2
    tasks = root / "openspec" / "changes" / change / "tasks.md"
    if tasks.exists():
        _mark_own_task(tasks, change)
    run(["npx", "-y", "@fission-ai/openspec@1.13.0", "archive", change, "-y"])
    if lock.exists():
        lock.unlink()
        print(f"removed {LOCK} left by a successful archive")
    run(["git", "add", "-A", "openspec"])
    run(["git", "commit", "-m", f"chore: archive {change}"])
    run(["git", "push"])
    pr = _pr_number(run)
    if (root / REVIEW_REQUEST).exists():
        run([sys.executable, str(REVIEW_REQUEST), "--request", str(pr)])
    else:
        print(f"note: {REVIEW_REQUEST} absent; no Codex review re-requested for PR #{pr}")
    return wait(pr)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("change", help="change name under openspec/changes/")
    ns = parser.parse_args(argv)
    try:
        sys.exit(finish_change(ns.change))
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
