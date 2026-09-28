#!/usr/bin/env python3
"""Read the repository's quality declaration (issue 249).

Usage: python skills/agent-process/scripts/quality.py --github-output

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
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path

DECLARATION = ".github/agent-process-quality.json"
_FIELDS = ("setup", "test", "checks")


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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read the repository's quality declaration.")
    parser.add_argument(
        "--github-output",
        action="store_true",
        required=True,
        help="append setup, test and checks to $GITHUB_OUTPUT",
    )
    parser.parse_args(sys.argv[1:] if argv is None else argv)
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
