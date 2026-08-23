#!/usr/bin/env python3
"""Create a fresh `issue-N-<slug>` branch from a GitHub issue title.

Usage: python scripts/issue_branch.py <issue-number>

Reads the issue title via `gh issue view`, derives a kebab-case ASCII
slug, and delegates to `scripts/new_branch.py` to do the actual checkout
(which itself guarantees branching from fresh origin/main HEAD). Once the
branch exists, it moves the issue's Status on the configured GitHub Project to
`In Progress` through `scripts/set_issue_status.py`.
"""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path
from types import ModuleType

MAX_SLUG_WORDS = 4
FALLBACK_SLUG = "task"


def slugify(title: str) -> str:
    ascii_only = re.sub(r"[^a-zA-Z0-9\s-]", " ", title).lower()
    words = [w for w in re.split(r"[\s-]+", ascii_only) if w]
    if not words:
        return FALLBACK_SLUG
    return "-".join(words[:MAX_SLUG_WORDS])


def _sibling_module(name: str) -> ModuleType:
    """Load a sibling `scripts/<name>.py` by absolute path and return the module.

    Loaded by absolute file path — NOT `from scripts.<name> import ...` —
    because the documented CLI `python scripts/issue_branch.py <N>` sets
    `sys.path[0]` to the script's dir (`scripts/`), and the repo root is never
    on `sys.path` (the editable install only adds `src/`). A package import
    would therefore raise `ModuleNotFoundError` at runtime even though
    `scripts/` IS a package (packageness is necessary but not sufficient; tests
    pass only because `python -m pytest` prepends the repo root). The path load
    is immune to `sys.path`, gives a single source of truth for
    `BRANCH_PREFIX`, and lets `main()` call `create_branch` in-process instead
    of re-spawning a second interpreter.
    """
    spec = importlib.util.spec_from_file_location(
        f"scripts.{name}", Path(__file__).with_name(f"{name}.py")
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _new_branch_module() -> ModuleType:
    return _sibling_module("new_branch")


def _require_project_bootstrap() -> None:
    """Stop before creating a branch when the copied process is still inactive."""
    try:
        _sibling_module("project_settings").require_configured()
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(2)


def _mark_in_progress(issue_number: int) -> None:
    """Move the issue's board card to `In Progress`, or stop delivery visibly.

    The branch must exist before its card claims `In Progress`. A branch cannot be
    safely deleted on a status failure, so report it as created and stop delivery
    rather than silently continuing with a stale card.
    """
    try:
        _sibling_module("set_issue_status").set_status(issue_number, "in-progress")
    except (RuntimeError, ValueError, OSError) as exc:
        print(
            f"error: branch for issue #{issue_number} was created, but its board status was "
            f"not moved to In Progress: {exc}. Delivery stopped; repair the status before continuing.",
            file=sys.stderr,
        )
        sys.exit(2)


def build_branch_name(issue_number: int, title: str) -> str:
    return f"{_new_branch_module().BRANCH_PREFIX}{issue_number}-{slugify(title)}"


def _fetch_title(issue_number: int) -> str:
    result = subprocess.run(
        ["gh", "issue", "view", str(issue_number), "--json", "title,state"],
        check=False,
        text=True,
        capture_output=True,
        encoding="utf-8",
    )
    if result.stdout is None or result.stderr is None:
        print(
            f"error: capture failed for `gh issue view {issue_number}` (rc={result.returncode})",
            file=sys.stderr,
        )
        sys.exit(2)
    if result.returncode != 0:
        detail = result.stderr.strip() or "no stderr"
        print(
            f"error: `gh issue view {issue_number}` failed (rc={result.returncode}): {detail}",
            file=sys.stderr,
        )
        sys.exit(2)
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        print(
            f"error: invalid JSON from `gh issue view {issue_number}`: {exc}",
            file=sys.stderr,
        )
        sys.exit(2)
    if data.get("state") != "OPEN":
        print(
            f"error: issue #{issue_number} is not OPEN (state={data.get('state')})",
            file=sys.stderr,
        )
        sys.exit(2)
    return data.get("title") or ""


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python scripts/issue_branch.py <issue-number>", file=sys.stderr)
        sys.exit(2)
    try:
        n = int(sys.argv[1])
    except ValueError:
        print(f"error: issue number must be int (got {sys.argv[1]!r})", file=sys.stderr)
        sys.exit(2)
    _require_project_bootstrap()
    title = _fetch_title(n)
    branch = build_branch_name(n, title)
    _new_branch_module().create_branch(branch)
    _mark_in_progress(n)


if __name__ == "__main__":
    main()
