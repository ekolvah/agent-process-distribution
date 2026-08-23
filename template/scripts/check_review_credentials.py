"""Preflight the credentials required by the two review carriers."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path


REVIEW_SECRET = "NOT_IMPLEMENTED"


def codex_app_slug() -> str:
    raise AssertionError("credential preflight is not implemented")


def workflow_secret_references(_workflows: Path) -> set[str]:
    raise AssertionError("credential preflight is not implemented")


def main(_argv: Sequence[str] | None = None) -> None:
    raise AssertionError("credential preflight is not implemented")
