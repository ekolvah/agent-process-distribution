# agent-process:managed
"""Claude `SessionStart` check: is the agent-process skill loaded for this project? (#187)

Usage: python .claude/agent-process-check.py <Install URL>

Silent when exactly one enabled install of the plugin applies to the project and holds the
skill. Otherwise, or when the check itself cannot decide, it prints the hook's JSON: a
`systemMessage` for the person and an `additionalContext` for the agent. It always exits 0: a
crashing hook is silent, and the marker is the carrier.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

PLUGIN = "agent-process@agent-process-marketplace"
MARKER = "agent-process skill not loaded"


def verdict(listing: Any, project: str) -> str | None:
    """The reason the skill is not loaded, `None` when it is."""
    if not isinstance(listing, list) or not all(isinstance(e, dict) for e in listing):
        return "cannot check: `claude plugin list --json` is not a list of objects"
    here = os.path.normcase(os.path.normpath(project))
    applying = [
        entry
        for entry in listing
        if entry.get("id") == PLUGIN
        and entry.get("enabled") is True
        and (
            entry.get("scope") == "user"
            or os.path.normcase(os.path.normpath(str(entry.get("projectPath", "")))) == here
        )
    ]
    if not applying:
        return "not enabled for this project"
    installs = {str(entry.get("installPath")): entry for entry in applying}
    if len(installs) > 1:
        versions = ", ".join(sorted(str(e.get("version")) for e in installs.values()))
        return f"several installs apply: {versions}"
    path, entry = next(iter(installs.items()))
    if not (Path(path) / "skills" / "agent-process" / "SKILL.md").is_file():
        return f"plugin {entry.get('version')} has no skill"
    return None


def _reason(argv: list[str]) -> str | None:
    if len(argv) != 1:
        return "cannot check: the hook passes no Install URL"
    claude = shutil.which("claude")
    if claude is None:
        return "cannot check: `claude` is not on PATH"
    done = subprocess.run(
        [claude, "plugin", "list", "--json"],
        capture_output=True,
        encoding="utf-8",
        timeout=10,
    )
    if done.returncode != 0:
        return f"cannot check: `claude plugin list --json` exited {done.returncode}: {done.stderr}"
    if done.stdout is None:
        return "cannot check: `claude plugin list --json` output not captured"
    try:
        listing = json.loads(done.stdout)
    except json.JSONDecodeError:
        return "cannot check: `claude plugin list --json` printed no JSON"
    return verdict(listing, os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())


def main(argv: list[str]) -> int:
    try:
        reason = _reason(argv)
    except Exception as exc:  # noqa: BLE001 - any failure is a reason, never a silent hook
        reason = f"cannot check: {type(exc).__name__}: {exc}"
    if reason is None:
        return 0
    fix = argv[0] if argv else "the Install section of the agent-process SKILL.md"
    print(
        json.dumps(
            {
                "systemMessage": f"{MARKER} ({reason}) — fix: {fix}",
                "hookSpecificOutput": {
                    "hookEventName": "SessionStart",
                    "additionalContext": (
                        f"{MARKER} ({reason}). Do not fetch, clone or reconstruct it; tell the "
                        f"person and wait. Fix: {fix}"
                    ),
                },
            }
        )  # ASCII escapes: a Windows console encoding cannot fail the print
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
