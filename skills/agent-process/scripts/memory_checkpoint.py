"""Memory checkpoint: a reminder after the agent writes into its auto-memory directory.

Auto-memory (`~/.claude/projects/<project>/memory/`) is machine-local. A fact that every
session and every person working on the repository needs belongs in the repository, where
they see it. Prose alone does not keep an agent to that rule.

It reminds rather than blocks. The path tells that a write went into memory, not what the
note is about, and the platform keeps preferences, corrections and project context there by
design. So it fires on every memory write and asks the agent the one question a path cannot
answer.

The plugin's `hooks/hooks.json` runs it as `agent-process memory_checkpoint post-edit`
(PostToolUse, matcher `Edit|Write`), with the hook JSON on stdin.
"""

from __future__ import annotations

import io
import json
import re
import sys
from typing import cast

# Anchored at `(^|/)` so a repository `.claude/rules/*` (no `projects/<x>/memory/` segment)
# and a stray `foo.claude/...` never match; `[^/]+` is the single project directory.
_MEMORY_DIR_RE = re.compile(r"(^|/)\.claude/projects/[^/]+/memory/")


def memory_path(payload: object) -> str | None:
    """The `tool_input.file_path` of the payload when it lies under auto-memory, else None."""
    tool_input = payload.get("tool_input") if isinstance(payload, dict) else None
    path = tool_input.get("file_path") if isinstance(tool_input, dict) else None
    if not isinstance(path, str) or _MEMORY_DIR_RE.search(path.replace("\\", "/")) is None:
        return None
    return path


def reminder(path: str) -> str:
    return (
        f"Wrote auto-memory file {path}. Does every session and every person working on "
        "this repository need this fact? If so, move it into the repository (its docs, "
        "rules, or scripts) and drop it here."
    )


def main() -> None:
    if sys.argv[1:] != ["post-edit"]:
        print(
            "usage: agent-process memory_checkpoint post-edit (reads the hook JSON on stdin)",
            file=sys.stderr,
        )
        sys.exit(2)
    # The hook JSON is UTF-8, and a Windows home directory can be non-ASCII; the default
    # Windows code page would fail on it with exit 1, which the agent never sees.
    cast(io.TextIOWrapper, sys.stderr).reconfigure(encoding="utf-8", errors="replace")
    try:
        payload = json.loads(sys.stdin.buffer.read().decode("utf-8", errors="replace") or "{}")
    except json.JSONDecodeError:
        payload = {}
    path = memory_path(payload)
    if path is None:
        sys.exit(0)
    # PostToolUse exit 2 shows stderr to the agent; the write has already happened.
    print(reminder(path), file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
