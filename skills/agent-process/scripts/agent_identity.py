#!/usr/bin/env python3
"""Run the agent under its own GitHub identity in this clone (change agent-identity).

Usage: agent-process agent_identity --bot <login> (--dry-run | --confirm)
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from pathlib import Path

import init
from set_status import Gh, run_gh

Git = Callable[[list[str]], "subprocess.CompletedProcess[str]"]


def bot_gh(token: str) -> Gh:
    raise NotImplementedError


def main(
    argv: list[str] | None = None,
    *,
    gh: Gh = run_gh,
    bot: Callable[[str], Gh] = bot_gh,
    git: Git = init.run,
    root: Path | None = None,
) -> None:
    raise NotImplementedError


if __name__ == "__main__":
    main()
