#!/usr/bin/env python3
"""Resolve one BLOCKING review thread the fixer's own correction addressed.

CI never infers whether a finding was addressed (ADR 0022): the required
check answers "may this PR merge?" from the workflow token, and this script
answers "I, the fixer, addressed this finding" from the maintainer's
authenticated local session. Different actor, credential, and trigger — never
wired into a workflow.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Sequence


def list_blocking(payload: object) -> list[tuple[str, str, str]]:
    """Return `(thread_id, priority, url)` for every open BLOCKING thread."""
    raise NotImplementedError


def resolve(payload: object, thread_id: str, *, mutate: Callable[[str], object]) -> None:
    """Resolve `thread_id`, refusing a thread reported against the current head."""
    raise NotImplementedError


def _parse_options(argv: Sequence[str] | None) -> argparse.Namespace:
    raise NotImplementedError


def main(argv: Sequence[str] | None = None) -> None:
    raise NotImplementedError


if __name__ == "__main__":
    main()
