"""Read one task's delivery metrics: start to merge beside the size, and review rounds.

Signature stub for RED; the implementation follows.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


class Prometheus(Protocol):
    def instant(self, expr: str) -> float | None:
        """The scalar of an instant query, or None when its result is empty."""


@dataclass(frozen=True)
class PullRequest:
    number: int
    merged_at: datetime | None
    merge_commit: str | None
    head_branch: str
    additions: int
    deletions: int


class GitHub(Protocol):
    def connected_prs(self, issue: int) -> list[PullRequest]:
        """The PRs of the issue's `ConnectedEvent`s."""

    def comments(self, pr: int) -> list[tuple[str, str]]:
        """Author login and body of each comment on the PR."""

    def tree(self, commit: str, path: str) -> list[str] | None:
        """Entry names of the directory at the commit, or None when it does not exist."""

    def blob(self, commit: str, path: str) -> str | None:
        """Text of the file at the commit, or None when it does not exist."""


class Unreadable(Exception):
    """A reading that cannot be taken: exit 2 naming the cause."""


def start_query(issue: int, attempt: int) -> str:
    raise NotImplementedError


def reading(issue: int, attempt: int, prometheus: Prometheus, github: GitHub) -> dict[str, object]:
    raise NotImplementedError


def main(
    argv: Sequence[str],
    environ: Mapping[str, str],
    *,
    prometheus: Callable[[str, str], Prometheus],
    github: GitHub,
) -> int:
    raise NotImplementedError
