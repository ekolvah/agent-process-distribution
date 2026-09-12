"""Owner-local task telemetry launcher (issue #101)."""

from __future__ import annotations

from typing import Protocol


class PullRequestSource(Protocol):
    """Read pull requests for an owner-local attempt ledger."""


def resolve_issue(explicit_issue: int | None, branch: str) -> str:
    raise NotImplementedError


def start_attempt(*args: object, **kwargs: object) -> object:
    raise NotImplementedError


def compose_claude_settings(*args: object, **kwargs: object) -> dict[str, object]:
    raise NotImplementedError


def run_claude(*args: object, **kwargs: object) -> int:
    raise NotImplementedError


def encode_codex_environment(*args: object, **kwargs: object) -> str:
    raise NotImplementedError


def decode_codex_environment(*args: object, **kwargs: object) -> object:
    raise NotImplementedError


def codex_command(*args: object, **kwargs: object) -> list[str]:
    raise NotImplementedError


def resolve_outcomes(*args: object, **kwargs: object) -> object:
    raise NotImplementedError


def check_host(*args: object, **kwargs: object) -> object:
    raise NotImplementedError
