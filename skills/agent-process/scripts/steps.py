"""The transition model `init.py` and its `onboarding` module share; not a command."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Callable


class InstallError(Exception):
    """A tool or command failed; exit 1."""


@dataclass
class Step:
    label: str
    status: str
    detail: str
    apply: Callable[[], bool] | None = None


if __name__ == "__main__":
    sys.exit("steps.py is imported by init.py; run `agent-process init`")
