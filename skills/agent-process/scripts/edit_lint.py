"""Edit-time lint: the project's `pre-commit`-stage hooks run on the file the agent just edited.

Without it a finding surfaces only at the pre-push gate or in CI. The project, not the
plugin, chooses the linters: they are the `pre-commit`-stage hooks of its own `.pre-commit-config.yaml`, the same declaration its gate
runs over all files. A project that declares none sees nothing.

The plugin's `hooks/hooks.json` runs it as `agent-process edit_lint post-edit` (PostToolUse,
matcher `Edit|Write`), with the hook JSON on stdin and the project as the working directory.
`pre-commit` runs in the root of the repository holding the edited file; a file outside an
adopted repository is not linted, and a repository git cannot read is a marker.
"""

from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import sys
from typing import cast

# git's messages for a directory in no repository (`(or any of the parent directories)` and
# `(or any parent up to mount point`) and for one inside a git directory. A `.git` file
# naming a missing directory prints `not a git repository: <gitdir>` and is not matched.
_NOT_REPOSITORY_CODE = (
    "fatal: not a git repository (or any ",
    "fatal: this operation must be run in a work tree",
)


def edited_path(payload: object) -> str | None:
    """The `tool_input.file_path` of the payload, or None when it carries none."""
    tool_input = payload.get("tool_input") if isinstance(payload, dict) else None
    path = tool_input.get("file_path") if isinstance(tool_input, dict) else None
    return path if isinstance(path, str) and path else None


def adopted_root(git: str, path: str) -> str | None:
    """The root of the repository holding `path` when it has adopted the process, else None.

    pre-commit takes the root and config from its working directory and makes `--files`
    relative to that root, so it runs there: a worktree is its own root.
    """
    # The failure is classified by git's message, so it must not be translated.
    env = {key: value for key, value in os.environ.items() if key != "LANGUAGE"}
    env["LC_ALL"] = "C"
    toplevel = subprocess.run(
        [git, "-C", os.path.dirname(path), "rev-parse", "--show-toplevel"],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        check=False,
    )
    if toplevel.stdout is None or toplevel.stderr is None:
        print("edit-time lint is not active: git output was not captured", file=sys.stderr)
        sys.exit(2)
    if toplevel.returncode != 0:
        # Exit 128 both when git finds no repository and when it refuses the one it found.
        if toplevel.stderr.startswith(_NOT_REPOSITORY_CODE):
            return None  # no repository, or inside a git directory: nothing to lint
        print(f"edit-time lint is not active: {toplevel.stderr}", file=sys.stderr, end="")
        sys.exit(2)
    root = toplevel.stdout.strip()
    adopted = os.path.isfile(os.path.join(root, ".github", "workflows", "agent-process.yml"))
    return root if adopted else None


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
    tools = {name: shutil.which(name) for name in ("pre-commit", "git")}
    for name, found in tools.items():
        if found is None:
            print(f"edit-time lint is not active: {name} is not on PATH", file=sys.stderr)
            sys.exit(2)
    pre_commit, git = cast(str, tools["pre-commit"]), cast(str, tools["git"])
    # The path stays absolute: pre-commit resolves a relative one against its working directory.
    path = os.path.abspath(path)
    root = adopted_root(git, path)
    if root is None:
        sys.exit(0)
    run = subprocess.run(
        [pre_commit, "run", "--hook-stage", "pre-commit", "--color", "never", "--files", path],
        cwd=root,
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
