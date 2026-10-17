#!/usr/bin/env python3
"""One session leads one task: the ledger binding a Claude Code session to an issue.

`finish_propose`, `start_change` and `archive_change` call `bind` with the change's
tracking issue and the session that `CLAUDE_CODE_SESSION_ID` names. The ledger is
`<git common dir>/agent-process/sessions`, one line `<session-id> <issue>` per binding, so every
worktree of a clone shares it; it is never committed. A session already bound to another issue
is refused (exit 2 in each script) before the script changes anything; an unset variable prints
`session not bound` and the script goes on. `archive_change` exports `sessions` of the issue
into the change, where the merged task's readings find them.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from pathlib import Path

VARIABLE = "CLAUDE_CODE_SESSION_ID"
PLACEHOLDER = "tracking issue <N>"
_TOKEN = re.compile(r"tracking issue (<N>|\d+)")


def tracking_issue(tasks_md: Path) -> int | None:
    """The `tracking issue <N>` token of tasks.md: `None` while it carries the placeholder, the
    number once the propose run wrote it. The first token in the file decides — Group 0 is
    the first group — so the literal `<N>`, the whole token or another `tracking issue <N>` in
    a later line (a test description, a quoted rule) is text. No token is a ValueError naming
    the convention."""
    match = _TOKEN.search(tasks_md.read_text(encoding="utf-8"))
    if match is None:
        raise ValueError(
            f"{tasks_md}: no `{PLACEHOLDER}` token and no `tracking issue <number>` — Group 0 of "
            "tasks.md carries the token and the propose run replaces it"
        )
    return None if match.group(1) == "<N>" else int(match.group(1))


class SessionLeadsAnotherIssue(ValueError):
    """The session is bound to another issue: the person opens a new session."""


def ledger_path(run: Callable[[list[str]], str], root: Path) -> Path:
    """The ledger of the clone `root` belongs to; git resolves the common dir."""
    common = run(
        ["git", "-C", str(root), "rev-parse", "--path-format=absolute", "--git-common-dir"]
    )
    return Path(common.strip()) / "agent-process" / "sessions"


def _read(ledger: Path) -> str:
    return ledger.read_text(encoding="utf-8") if ledger.exists() else ""


def _bindings(text: str) -> dict[str, int]:
    bindings: dict[str, int] = {}
    for line in text.splitlines():
        session, _, issue = line.partition(" ")
        bindings[session] = int(issue)
    return bindings


def bind(issue: int | None, *, environ: Mapping[str, str], ledger: Callable[[], Path]) -> None:
    """Bind the session to `issue`. `None` (an issue not created yet) only refuses a session
    that leads one already. `ledger` is resolved once the session is known."""
    session = environ.get(VARIABLE)
    if not session:
        print(f"session not bound: {VARIABLE} is unset")
        return
    path = ledger()
    try:
        text = _read(path)
        led = _bindings(text).get(session)
        if led is None and issue is not None:
            path.parent.mkdir(parents=True, exist_ok=True)
            sep = "" if not text or text.endswith("\n") else "\n"
            with path.open("a", encoding="utf-8") as f:
                f.write(f"{sep}{session} {issue}\n")
    except OSError as exc:
        raise RuntimeError(f"cannot bind session {session} in {path}: {exc}") from exc
    if led is not None and led != issue:
        target = "the new issue" if issue is None else f"issue-{issue}"
        raise SessionLeadsAnotherIssue(
            f"session {session} already leads issue-{led}; open a new session for {target}"
        )


def sessions(issue: int, *, ledger: Path) -> list[str]:
    """The sessions bound to `issue`, sorted."""
    return sorted(s for s, i in _bindings(_read(ledger)).items() if i == issue)
