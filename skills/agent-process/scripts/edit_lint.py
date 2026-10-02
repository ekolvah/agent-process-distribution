"""Edit-time lint: the project's `pre-commit`-stage hooks run on the file the agent just edited.

Without it a finding surfaces only at the pre-push gate or in CI, and the plugin shipped no
edit-time check at all (#321). The project, not the plugin, chooses the linters: they are the
`pre-commit`-stage hooks of its own `.pre-commit-config.yaml`, the same declaration its gate
runs over all files. A project that declares none sees nothing.

The plugin's `hooks/hooks.json` runs it as `agent-process edit_lint post-edit` (PostToolUse,
matcher `Edit|Write`), with the hook JSON on stdin and the project as the working directory.
"""

from __future__ import annotations

import io
import json
import shutil
import subprocess
import sys
from typing import cast


def edited_path(payload: object) -> str | None:
    """The `tool_input.file_path` of the payload, or None when it carries none."""
    tool_input = payload.get("tool_input") if isinstance(payload, dict) else None
    path = tool_input.get("file_path") if isinstance(tool_input, dict) else None
    return path if isinstance(path, str) and path else None


def main() -> None:
    if sys.argv[1:] != ["post-edit"]:
        print(
            "usage: agent-process edit_lint post-edit (reads the hook JSON on stdin)",
            file=sys.stderr,
        )
        sys.exit(2)
    # The hook JSON and the linters' output are UTF-8; the default Windows code page would
    # fail on a non-ASCII path with exit 1, which the agent never sees.
    cast(io.TextIOWrapper, sys.stderr).reconfigure(encoding="utf-8", errors="replace")
    try:
        payload = json.loads(sys.stdin.buffer.read().decode("utf-8", errors="replace") or "{}")
    except json.JSONDecodeError:
        payload = {}
    path = edited_path(payload)
    if path is None:
        sys.exit(0)
    pre_commit = shutil.which("pre-commit")
    if pre_commit is None:
        print("edit-time lint is not active: pre-commit is not on PATH", file=sys.stderr)
        sys.exit(2)
    run = subprocess.run(
        [pre_commit, "run", "--hook-stage", "pre-commit", "--color", "never", "--files", path],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if run.stdout is None or run.stderr is None:
        print("edit-time lint is not active: pre-commit output was not captured", file=sys.stderr)
        sys.exit(2)
    if run.returncode == 0:
        sys.exit(0)
    # PostToolUse exit 2 shows stderr to the agent; the edit has already happened. A finding
    # and pre-commit's own error both exit 1, and both reach the agent as text.
    print(run.stdout + run.stderr, file=sys.stderr, end="")
    sys.exit(2)


if __name__ == "__main__":
    main()
