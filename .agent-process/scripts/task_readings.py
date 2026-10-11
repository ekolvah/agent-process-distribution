#!/usr/bin/env python3
"""Record one merged task PR's readings as a row of `task-readings.csv`."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Protocol

COLUMNS = (
    "pr",
    "change",
    "task_id",
    "attempt_id",
    "start",
    "merged_at",
    "hours",
    "lines",
    "plan_rounds",
    "code_rounds",
    "cost_usd",
    "api_requests",
    "failed",
    "denied",
    "compactions",
    "unlaunched_events",
    "gap",
)


class GitHub(Protocol):
    def pull_request(self, pr: int) -> Mapping[str, object]: ...


class Grafana(Protocol):
    def prometheus(self, query: str, time: float) -> list[Mapping[str, object]]: ...

    def loki(self, query: str, time: float) -> list[Mapping[str, object]]: ...


def main(argv: Sequence[str], environ: Mapping[str, str], github: GitHub, grafana: Grafana) -> int:
    raise NotImplementedError
