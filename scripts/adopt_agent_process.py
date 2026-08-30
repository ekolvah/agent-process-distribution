#!/usr/bin/env python3
"""Adopt reserved agent-process files without replacing consumer configuration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class _Markers:
    managed: tuple[str, str] = ("<!-- agent-process:begin -->", "<!-- agent-process:end -->")


@dataclass(frozen=True)
class PreflightReport:
    collisions: tuple[str, ...]


CONFLICT_MARKERS = _Markers()


def preflight(destination: Path, payload: dict[str, bytes]) -> PreflightReport:
    return PreflightReport(())


def install_payload(destination: Path, payload: dict[str, bytes]) -> None:
    """Install a payload after preflight (implemented in the GREEN change)."""


def update_payload(destination: Path, payload: dict[str, bytes]) -> None:
    """Update a payload after preflight (implemented in the GREEN change)."""


def update_managed_fragment(path: Path, content: str) -> None:
    """Update one explicitly delimited fragment (implemented in the GREEN change)."""
