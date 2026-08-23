"""Compare the self-applied root with a fresh working-tree render."""

from __future__ import annotations

from pathlib import Path


def check(root: Path) -> list[str]:
    """Return drift findings for the source repository root."""
    del root
    return ["template drift gate is not implemented"]
