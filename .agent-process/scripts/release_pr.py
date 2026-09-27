#!/usr/bin/env python3
"""Publish whether a PR is a release PR: `release=true|false` (ADR 0031)."""

from __future__ import annotations

from collections.abc import Sequence

try:
    from scripts.gh_io import publish_step_output, run_gh
except ModuleNotFoundError:  # run as a script from `.agent-process/`
    from gh_io import publish_step_output, run_gh

__all__ = ["publish_step_output", "run_gh"]


def release_verdict(
    config: dict | None,
    changes: list[tuple[str, str]],
    base_text: dict[str, str],
    head_text: dict[str, str],
) -> str | None:
    raise NotImplementedError


def main(argv: Sequence[str] | None = None) -> None:
    raise NotImplementedError
