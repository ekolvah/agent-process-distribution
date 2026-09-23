#!/usr/bin/env python3
"""Install the agent process into a consumer repository (signature stub for RED)."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Callable

VERSION: str | None = None
OPENSPEC_OUTPUT: tuple[str, ...] = ()


def run(
    cmd: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    capture: bool = True,
) -> subprocess.CompletedProcess[str]:
    raise NotImplementedError


def render_workflow(version: str, setup: str, test: str) -> str:
    raise NotImplementedError


def render_config_block(test: str) -> str:
    raise NotImplementedError


def install(
    argv: list[str],
    *,
    root: Path,
    home: Path,
    platform: str,
    runner: Callable[..., Any],
    which: Callable[[str], str | None],
    on_write: Callable[[str], None],
) -> int:
    raise NotImplementedError
