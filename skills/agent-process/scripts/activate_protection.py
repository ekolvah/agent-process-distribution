#!/usr/bin/env python3
"""Make `agent-process / quality` required on the default branch once it has been observed.

Usage: python skills/agent-process/scripts/activate_protection.py --pr <N> (--dry-run | --confirm)
"""

from __future__ import annotations

from set_status import Gh, run_gh


def main(argv: list[str] | None = None, *, gh: Gh = run_gh) -> None:
    raise NotImplementedError
