#!/usr/bin/env python3
"""Archive a change before its PR opens: mark the own task, archive, commit, push.

Usage: python skills/agent-process/scripts/archive_change.py <change>

A Deliver task of every `tasks.md`, run before `gh pr create` so the head the review reads
is the archived one and no push follows the last review round. `openspec archive` moves
`tasks.md` into the archive, so nothing can mark this task after it ran: the script marks
its own box first (the whole task item, continuation lines included), then archives,
removes the lock a successful archive leaves behind, commits and pushes. The review
request and `wait_for_pr` are the PR tasks that follow; they leave no tick in the
repository (a pushed tick would move the reviewed head) — the PR is their record. The
change's own `tasks.md`, modified only, is the one uncommitted change it takes: the Verify
ticks ride in the archive commit. Once the worktree is clean, the session is bound to the
tracking issue (`session_binding`) and every session bound to it is written, sorted, to the
change's `sessions`, which the archive carries to the merged task's readings; a `sessions` left
by a failed archive is rewritten. After the archive, `openspec validate --strict` runs on each
main spec the change has a delta for; a failure, such as the placeholder Purpose the archive
writes for a new capability without one, stops before the commit. The fix is a direct edit
of that main spec; the re-run finds the archive uncommitted and resumes at the validation,
accepting uncommitted paths under `openspec/` only. Exit codes: 0 done; 1 when a command
fails; 2 when the worktree holds any other change (the archive commit must be the only thing
left to push, and the offending paths are printed), when the session leads another issue,
when a touched main spec does not validate (OpenSpec's findings are printed), or when
`openspec/changes/archive/.openspec-archive.lock` already exists — a previous
archive aborted and its state must be inspected before anything is archived on top of it.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

from init import OPENSPEC
from session_binding import bind, ledger_path, sessions, tracking_issue

Run = Callable[[list[str]], str]
LOCK = Path("openspec", "changes", "archive", ".openspec-archive.lock")
OPENSPEC_CMD = ["npx", "-y", f"@fission-ai/openspec@{OPENSPEC}"]


def _runner(root: Path) -> Run:
    def run(cmd: list[str]) -> str:
        exe = shutil.which(cmd[0]) or cmd[0]
        # `errors="replace"`: the pre-push hook's pytest output can carry a code-page
        # byte on Windows; a mangled character keeps the hook's finding visible, a dead
        # reader thread hides it behind "broken capture" (§IV, as edit_lint.py).
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


def mark_own_task(tasks: Path, script: str, change: str) -> None:
    """Tick the task item naming `agent-process <script> <change>` anywhere in its lines.

    The older `<script>.py <change>` of an in-flight `tasks.md` ticks too.
    """
    text = tasks.read_text(encoding="utf-8")
    # A task item runs from its `- [ ] ` line to the next list item or heading.
    item = re.compile(r"^- \[ \] (?:(?!^- \[|^#).)*", re.M | re.S)
    command = re.compile(rf"{re.escape(script)}(?:\.py)? {re.escape(change)}\b")
    for match in item.finditer(text):
        if command.search(match.group()):
            text = text[: match.start()] + "- [x] " + text[match.start() + len("- [ ] ") :]
            tasks.write_text(text, encoding="utf-8")
            return
    print(f"note: no unchecked `agent-process {script} {change}` task in {tasks}; nothing marked")


def _uncommitted_archive(root: Path, change: str, status: list[str]) -> str | None:
    """The `openspec/changes/archive/<date>-<change>` that `git status` lists, once the
    change itself is gone, if any."""
    if (root / "openspec" / "changes" / change).exists():
        return None
    archived = re.compile(
        rf"(openspec/changes/archive/\d{{4}}-\d{{2}}-\d{{2}}-{re.escape(change)})/"
    )
    for line in status:
        if match := archived.match(line[3:]):
            return match.group(1)
    return None


def _capabilities(deltas: Path) -> list[str]:
    """The capability of each delta `spec.md` under `deltas`, named by its path."""
    return sorted(p.parent.relative_to(deltas).as_posix() for p in deltas.rglob("spec.md"))


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
    status = run(["git", "status", "--porcelain", "--untracked-files=all"]).splitlines()
    change_dir = root / "openspec" / "changes" / change
    archived = _uncommitted_archive(root, change, status)
    capabilities = _capabilities((root / archived if archived else change_dir) / "specs")
    if archived:
        # A refused validation left the archive uncommitted: the archived `sessions` and
        # `tasks.md` already carry the binding and the tick, so resume at the validation.
        dirty = [line for line in status if not line[3:].startswith("openspec/")]
        why = f"{archived} is not committed yet; only openspec/ may change before the re-run"
    else:
        # The Verify ticks are the one change the archive commit carries: `openspec archive`
        # moves `tasks.md`, so no later commit could.
        # A failed `openspec archive` leaves the exported `sessions`; the re-run rewrites it.
        own = f"openspec/changes/{change}/tasks.md"
        exported = f"openspec/changes/{change}/sessions"
        dirty = [
            line
            for line in status
            if not (line[:2] in (" M", "M ", "MM") and line[3:] == own) and line[3:] != exported
        ]
        why = "the worktree is not clean"
    if dirty:
        print(
            f"error: {why} — commit or drop these before archiving, or the pushed head would "
            "not carry them:\n" + "\n".join(dirty),
            file=sys.stderr,
        )
        return 2
    if not archived:
        tasks = change_dir / "tasks.md"
        issue = tracking_issue(tasks)
        ledger = ledger_path(run, root)
        bind(issue, environ=os.environ, ledger=lambda: ledger)
        ids = sessions(issue, ledger=ledger) if issue is not None else []
        (tasks.parent / "sessions").write_text("".join(f"{s}\n" for s in ids), encoding="utf-8")
        mark_own_task(tasks, "archive_change", change)
        run([*OPENSPEC_CMD, "archive", change, "-y"])
        if lock.exists():
            lock.unlink()
            print(f"removed {LOCK} left by a successful archive")
    # `openspec archive` writes a placeholder Purpose into a capability its delta creates
    # without one, and validates nothing it wrote: strict validation of each touched main
    # spec stops that placeholder before the commit (a retired capability has no main spec).
    touched = [c for c in capabilities if (root / "openspec" / "specs" / c / "spec.md").exists()]
    failed = []
    for capability in touched:
        try:
            run([*OPENSPEC_CMD, "validate", capability, "--type", "spec", "--strict"])
        except RuntimeError as exc:
            print(f"error: {exc}", file=sys.stderr)
            failed.append(capability)
    if failed:
        specs = ", ".join(f"openspec/specs/{c}/spec.md" for c in failed)
        print(
            f"error: nothing was committed; replace the placeholder Purpose in {specs} by a "
            f"direct edit, then re-run `agent-process archive_change {change}`",
            file=sys.stderr,
        )
        return 2
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
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(2)
    except (OSError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
