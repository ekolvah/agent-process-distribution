#!/usr/bin/env python3
"""One session leads one task: the ledger binding a Claude Code session to an issue."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path


def bind(issue: int | None, *, environ: Mapping[str, str], ledger: Callable[[], Path]) -> None:
    raise NotImplementedError


def sessions(issue: int, *, ledger: Path) -> list[str]:
    raise NotImplementedError
