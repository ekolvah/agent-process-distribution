#!/usr/bin/env python3
"""Read the repository's quality declaration (issue 249).

Usage: python skills/agent-process/scripts/quality.py (--github-output | --hook)

`.github/agent-process-quality.json` belongs to the repository, not to the installer: a
repository without tests has no command to declare, and the change that adds the first
tests declares it. The file is one JSON object:

    {"setup": "<command>", "test": "<command>", "checks": "<command>"}

`test` is required and non-blank; `setup` (run before it) and `checks` (prints a JSON
array of check names, each run as `test --only <name>` in its own job) are optional. Every
value is a single line: it becomes one `name=value` line of `$GITHUB_OUTPUT`.

`--github-output` is the reusable `quality` workflow's reader: it appends `setup`, `test`
and `checks` to `$GITHUB_OUTPUT`. An absent file is a warning annotation and empty outputs
(CI runs no tests, visibly); a malformed one is an error annotation and exit 1. `check_red`
and the installer call `read`.

`hook` is the pre-push hook (issue 188): the console script `agent-process-quality` for a
consumer, through pre-commit, and `--hook` for this repository. It runs the declared `test`
once through `bash` and exits with its code.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

DECLARATION = ".github/agent-process-quality.json"
_FIELDS = ("setup", "test", "checks")
BASH = "bash"
GIT = "git"


@dataclass(frozen=True)
class Declaration:
    setup: str
    test: str
    checks: str


def read(root: Path) -> Declaration | None:
    """The declaration under `root`; `None` when the file is absent. A file that declares
    no usable `test` raises `ValueError` naming the file and the fault."""
    path = root / DECLARATION
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise ValueError(f"{DECLARATION}: not readable JSON ({exc})") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{DECLARATION}: not a JSON object")
    values = {}
    for name in _FIELDS:
        value = data.get(name, "")
        if not isinstance(value, str):
            raise ValueError(f"{DECLARATION}: `{name}` is not a string")
        if "\n" in value or "\r" in value:
            raise ValueError(f"{DECLARATION}: `{name}` holds a line break")
        values[name] = value
    if "test" not in data:
        raise ValueError(f"{DECLARATION}: declares no `test`")
    if not values["test"].strip():
        raise ValueError(f"{DECLARATION}: `test` is blank")
    return Declaration(**values)


def _pushed_env(hook_env: bool) -> dict[str, str] | str:
    """The environment the declared test runs in, or the fault that stops the push."""
    git = shutil.which(GIT)
    if git is None:
        return f"`{GIT}` is not on PATH; the repository-local git environment cannot be listed"
    listed = subprocess.run(
        [git, "rev-parse", "--local-env-vars"],
        capture_output=True,
        encoding="utf-8",
        check=False,
    )
    if listed.returncode != 0:
        return f"`{GIT} rev-parse --local-env-vars` failed: {listed.stderr.strip()}"
    names = listed.stdout.split()
    if not names:
        return f"`{GIT} rev-parse --local-env-vars` printed no names"
    env = {key: value for key, value in os.environ.items() if key not in names}
    if hook_env:
        # pre-commit's `language: python` env, which only this console script runs from.
        own = os.path.normcase(os.path.dirname(sys.executable))
        path = env.get("PATH", "").split(os.pathsep)
        env["PATH"] = os.pathsep.join(p for p in path if os.path.normcase(p) != own)
        if env.get("VIRTUAL_ENV") == sys.prefix:
            del env["VIRTUAL_ENV"]
    return env


def hook(hook_env: bool = True) -> int:
    """The pre-push hook: run the declared `test` once, as CI does, and return its exit code.

    `hook_env` is true on the console script `agent-process-quality`, which pre-commit runs
    from the hook env it built; `quality.py --hook` runs in the pusher's own environment."""
    try:
        declared = read(Path.cwd())
    except ValueError as exc:
        print(f"quality: {exc}", file=sys.stderr)
        return 1
    if declared is None:
        print(
            f"quality: {DECLARATION} is absent: no quality command is declared, so no test runs",
            file=sys.stderr,
        )
        return 0
    env = _pushed_env(hook_env)
    if isinstance(env, str):
        print(f"quality: {env}", file=sys.stderr)
        return 2
    bash = shutil.which(BASH, path=env.get("PATH"))
    if bash is None:
        print(
            f"quality: `{BASH}` is not on PATH; the declared test is a bash command",
            file=sys.stderr,
        )
        return 2
    return subprocess.run([bash, "-c", declared.test], env=env, check=False).returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read the repository's quality declaration.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--github-output",
        action="store_true",
        help="append setup, test and checks to $GITHUB_OUTPUT",
    )
    mode.add_argument(
        "--hook",
        action="store_true",
        help="run the declared test in the pusher's environment (this repository's pre-push)",
    )
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    if args.hook:
        return hook(hook_env=False)
    try:
        declared = read(Path.cwd())
    except ValueError as exc:
        print(f"::error::{exc}")
        return 1
    if declared is None:
        print(
            f"::warning::{DECLARATION} declares no test: CI runs no tests until the change "
            'that adds the first tests declares {"test": "<command>"}'
        )
        declared = Declaration(setup="", test="", checks="")
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
        for name in _FIELDS:
            output.write(f"{name}={getattr(declared, name)}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
