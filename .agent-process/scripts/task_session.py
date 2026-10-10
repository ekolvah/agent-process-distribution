#!/usr/bin/env python3
"""Launch a Claude Code session that carries the task identity on its telemetry.

    python .agent-process/scripts/task_session.py --issue N [--attempt K] -- claude [args...]

The command gets one `--settings` JSON layer after its executable. Its `env` holds the
project's `OTEL_RESOURCE_ATTRIBUTES` plus `task_id=issue-N,attempt_id=K`, and the variables
that send this session's traces to the local Alloy receiver. The process environment cannot
carry the attributes: the project's `.claude/settings.json` value replaces it. See ADR 0037.
Exits 2 naming the cause on bad arguments or project settings; otherwise with the command's
exit code.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Protocol

_IDENTITY_KEYS = ("task_id", "attempt_id")
_TRACES_ENV = {
    "CLAUDE_CODE_ENHANCED_TELEMETRY_BETA": "1",
    "OTEL_TRACES_EXPORTER": "otlp",
    "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT": "http://127.0.0.1:4318/v1/traces",
    "OTEL_EXPORTER_OTLP_TRACES_PROTOCOL": "http/protobuf",
}


class Runner(Protocol):
    def __call__(self, command: list[str]) -> int: ...


class _UsageError(Exception):
    pass


def compose_attributes(project_value: str, issue: int, attempt: int) -> str:
    keys = {pair.split("=", 1)[0].strip() for pair in project_value.split(",")}
    for key in _IDENTITY_KEYS:
        if key in keys:
            raise ValueError(f"project OTEL_RESOURCE_ATTRIBUTES already names {key}")
    return f"{project_value},task_id=issue-{issue},attempt_id={attempt}"


def settings_layer(attributes: str) -> str:
    return json.dumps({"env": {"OTEL_RESOURCE_ATTRIBUTES": attributes, **_TRACES_ENV}})


def _positive(text: str) -> int:
    if not text.isdigit() or int(text) < 1:
        raise argparse.ArgumentTypeError(f"not a positive integer: {text!r}")
    return int(text)


def _project_value() -> str:
    top = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], capture_output=True, encoding="utf-8"
    )
    if top.returncode != 0:
        raise _UsageError(f"not inside a Git work tree: {top.stderr.strip()}")
    path = Path(top.stdout.strip()) / ".claude" / "settings.json"
    if not path.is_file():
        raise _UsageError(f"{path} does not exist")
    value = (
        json.loads(path.read_text(encoding="utf-8")).get("env", {}).get("OTEL_RESOURCE_ATTRIBUTES")
    )
    if not value:
        raise _UsageError(f"{path} sets no env.OTEL_RESOURCE_ATTRIBUTES")
    return value


def main(argv: Sequence[str], runner: Runner) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--issue", type=_positive, required=True)
    parser.add_argument("--attempt", type=_positive, default=1)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        parser.error("no command after --")
    try:
        attributes = compose_attributes(_project_value(), args.issue, args.attempt)
    except (_UsageError, ValueError) as exc:
        print(f"task_session: {exc}", file=sys.stderr)
        return 2
    return runner([command[0], "--settings", settings_layer(attributes), *command[1:]])


def _subprocess_runner(command: list[str]) -> int:
    # An npm-installed `claude` is a `.cmd` shim, which CreateProcess finds only by full path.
    executable = shutil.which(command[0])
    if executable is None:
        print(f"task_session: {command[0]} not found on PATH", file=sys.stderr)
        return 2
    return subprocess.run([executable, *command[1:]]).returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:], _subprocess_runner))
