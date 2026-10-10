#!/usr/bin/env python3
"""Launch a Claude Code session that carries the task identity on its telemetry.

python .agent-process/scripts/task_session.py --issue N [--attempt K] -- claude [args...]
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol


class Runner(Protocol):
    def __call__(self, command: list[str]) -> int: ...


def compose_attributes(project_value: str, issue: int, attempt: int) -> str:
    raise NotImplementedError


def settings_layer(attributes: str) -> str:
    raise NotImplementedError


def main(argv: Sequence[str], runner: Runner) -> int:
    raise NotImplementedError
