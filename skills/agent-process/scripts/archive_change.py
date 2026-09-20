#!/usr/bin/env python3
"""Archive a change before its PR opens: mark the own task, archive, commit, push.

Usage: python .agent-process/scripts/archive_change.py <change>

A Deliver task of every `tasks.md`, run before `gh pr create` so the head the review reads
is the archived one and no push follows the last review round. `openspec archive` moves
`tasks.md` into the archive, so nothing can mark this task after it ran: the script marks
its own box first (the whole task item, continuation lines included), then archives,
removes the lock a successful archive leaves behind, commits and pushes. The review
request and `wait_for_pr` are the PR tasks that follow; they leave no tick in the
repository (a pushed tick would move the reviewed head) — the PR is their record. Exit
codes: 0 done; 1 when a command
fails; 2 when the worktree is not clean (the archive commit must be the only thing left to
push) or when `openspec/changes/archive/.openspec-archive.lock` already exists — a previous
archive aborted and its state must be inspected before anything is archived on top of it.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

Run = Callable[[list[str]], str]
LOCK = Path("openspec", "changes", "archive", ".openspec-archive.lock")


def _runner(root: Path) -> Run:
    def run(cmd: list[str]) -> str:
        exe = shutil.which(cmd[0]) or cmd[0]
        # `errors="replace"`: the pre-push hook's pytest output can carry a code-page
        # byte on Windows; a mangled character keeps the hook's finding visible, a dead
        # reader thread hides it behind "broken capture" (§IV, as hooks.py).
        result = subprocess.run(
            [exe, *cmd[1:]],
            cwd=root,
            text=True,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
        )
        if result.stdout is None or result.stderr is None:
            raise RuntimeError(f"`{' '.join(cmd)}`: broken capture (stdout or stderr is None)")
        if result.returncode != 0:
            detail = (result.stderr or result.stdout).strip() or "no output"
            raise RuntimeError(f"`{' '.join(cmd)}` failed (rc={result.returncode}): {detail}")
        return result.stdout

    return run


def _mark_own_task(tasks: Path, change: str) -> None:
    """Tick the task item naming `archive_change.py <change>` anywhere in its lines."""
    text = tasks.read_text(encoding="utf-8")
    # A task item runs from its `- [ ] ` line to the next list item or heading.
    item = re.compile(r"^- \[ \] (?:(?!^- \[|^#).)*", re.M | re.S)
    command = re.compile(rf"archive_change\.py {re.escape(change)}\b")
    for match in item.finditer(text):
        if command.search(match.group()):
            text = text[: match.start()] + "- [x] " + text[match.start() + len("- [ ] ") :]
            tasks.write_text(text, encoding="utf-8")
            return
    print(f"note: no unchecked `archive_change.py {change}` task in {tasks}; nothing marked")


def archive_change(change: str, *, root: Path = Path("."), run: Run | None = None) -> int:
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
    return 0


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("change", help="change name under openspec/changes/")
    ns = parser.parse_args(argv)
    try:
        sys.exit(archive_change(ns.change))
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
