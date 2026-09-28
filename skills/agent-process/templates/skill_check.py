# agent-process:managed
"""Claude `SessionStart` check: is the agent-process skill loaded for this project? (#187)

Usage: python .claude/agent-process-check.py <Install URL>

Silent when exactly one enabled user-scope install of the plugin exists and holds the skill, and
no install of another scope applies to the project. A project-level install is reported with the
command that removes it; any other case, or a check that cannot decide, is `skill not loaded`.
Either way it prints the hook's JSON: a `systemMessage` for the person and an `additionalContext`
for the agent. It always exits 0: a crashing hook is silent, and the marker is the carrier.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

PLUGIN = "agent-process@agent-process-marketplace"
MARKER = "agent-process skill not loaded"
PROJECT_MARKER = "agent-process project-scope install applies"


def verdict(listing: Any, project: str) -> tuple[str, str] | None:
    """`(headline, reason)` when the person must act, `None` when the skill is loaded."""
    if not isinstance(listing, list) or not all(isinstance(e, dict) for e in listing):
        return MARKER, "cannot check: `claude plugin list --json` is not a list of objects"
    here = _folded(project)
    enabled = [e for e in listing if e.get("id") == PLUGIN and e.get("enabled") is True]
    local = [
        e
        for e in enabled
        if e.get("scope") != "user" and _folded(str(e.get("projectPath", ""))) == here
    ]
    if local:
        return PROJECT_MARKER, "; ".join(f"{e.get('version')}: {_removal(e)}" for e in local)
    users = [e for e in enabled if e.get("scope") == "user"]
    if not users:
        return MARKER, f"not installed at user scope: claude plugin install {PLUGIN}"
    installs = {str(entry.get("installPath")): entry for entry in users}
    if len(installs) > 1:
        versions = ", ".join(sorted(str(e.get("version")) for e in installs.values()))
        return MARKER, f"several user-scope installs: {versions}"
    path, entry = next(iter(installs.items()))
    if not (Path(path) / "skills" / "agent-process" / "SKILL.md").is_file():
        return MARKER, f"plugin {entry.get('version')} has no skill"
    return None


def _removal(entry: dict[str, Any]) -> str:
    """The command removing a project-level install: `uninstall` picks the record by the cwd's
    exact spelling, and only cmd's `cd /d` keeps a lowercase drive letter."""
    path = str(entry.get("projectPath"))
    cd = "cd /d" if re.match(r"^[A-Za-z]:", path) else "cd"
    return f'{cd} "{path}" && claude plugin uninstall {PLUGIN} --scope {entry.get("scope")}'


def _folded(path: str) -> str:
    """A project path compared ignoring case on every OS: `normcase` folds only on Windows."""
    return os.path.normpath(path).casefold()


def _verdict(argv: list[str]) -> tuple[str, str] | None:
    if len(argv) != 1:
        return MARKER, "cannot check: the hook passes no Install URL"
    claude = shutil.which("claude")
    if claude is None:
        return MARKER, "cannot check: `claude` is not on PATH"
    done = subprocess.run(
        [claude, "plugin", "list", "--json"],
        capture_output=True,
        encoding="utf-8",
        timeout=10,
    )
    if done.returncode != 0:
        return (
            MARKER,
            f"cannot check: `claude plugin list --json` exited {done.returncode}: {done.stderr}",
        )
    if done.stdout is None:
        return MARKER, "cannot check: `claude plugin list --json` output not captured"
    try:
        listing = json.loads(done.stdout)
    except json.JSONDecodeError:
        return MARKER, "cannot check: `claude plugin list --json` printed no JSON"
    return verdict(listing, os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())


def main(argv: list[str]) -> int:
    try:
        found = _verdict(argv)
    except Exception as exc:  # noqa: BLE001 - any failure is a reason, never a silent hook
        found = MARKER, f"cannot check: {type(exc).__name__}: {exc}"
    if found is None:
        return 0
    headline, reason = found
    fix = argv[0] if argv else "the Install section of the agent-process SKILL.md"
    advice = (
        "Tell the person to run these commands and restart the session."
        if headline == PROJECT_MARKER
        else "Do not fetch, clone or reconstruct it; tell the person and wait."
    )
    print(
        json.dumps(
            {
                "systemMessage": f"{headline} ({reason}) — fix: {fix}",
                "hookSpecificOutput": {
                    "hookEventName": "SessionStart",
                    "additionalContext": f"{headline} ({reason}). {advice} Fix: {fix}",
                },
            }
        )  # ASCII escapes: a Windows console encoding cannot fail the print
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
