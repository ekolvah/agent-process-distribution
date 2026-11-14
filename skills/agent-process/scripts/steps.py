"""The transition model and the process boundary `init.py` and its modules share; not a
command."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


class InstallError(Exception):
    """A tool or command failed; exit 1."""


@dataclass
class Step:
    label: str
    status: str
    detail: str
    apply: Callable[[], bool] | None = None

    @property
    def line(self) -> str:
        return f"{self.status} {self.label}: {self.detail}"


def run(
    cmd: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    capture: bool = True,
    input: str | None = None,
) -> subprocess.CompletedProcess[str]:
    """The process boundary. Captured output is UTF-8; uncaptured output goes to this
    process's own streams and `stdout`/`stderr` stay `None`. `input` is the command's
    standard input."""
    return subprocess.run(
        [str(part) for part in cmd],
        cwd=cwd,
        env=env,
        input=input,
        capture_output=capture,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


if __name__ == "__main__":
    sys.exit("steps.py is imported by init.py; run `agent-process init`")
