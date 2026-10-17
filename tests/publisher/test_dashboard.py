"""The per-task dashboard renders for a list of repositories.

Driven through the CLI only: `dashboard.py <owner/name>...` prints the dashboard JSON on
stdout; a malformed argument or none exits 2 with nothing on stdout.
"""

from __future__ import annotations

import json
import subprocess
import sys

import pytest

from tests.publisher.delivery_fakes import SKILL_SCRIPTS

_SCRIPT = SKILL_SCRIPTS / "dashboard.py"
_KINOZAL = "ekolvah/kinozal_scraper"
_OTHER = "ekolvah/agent-process-distribution"
_LINK = "https://github.com/${__data.fields.repository}/issues/${__data.fields.issue}"


def _run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, _SCRIPT, *args],
        capture_output=True,
        encoding="utf-8",
        check=False,
    )


def _render(*repositories: str) -> tuple[str, dict]:
    result = _run(list(repositories))
    assert result.returncode == 0, result.stderr
    return result.stdout, json.loads(result.stdout)


def _data_panels(dashboard: dict) -> list[dict]:
    return [panel for panel in dashboard["panels"] if "targets" in panel]


def _url(repository: str) -> str:
    return f"https://raw.githubusercontent.com/{repository}/task-readings/task-readings.csv"


def _computed(target: dict) -> dict[str, str]:
    return {column["text"]: column["selector"] for column in target["computed_columns"]}


def _table(dashboard: dict) -> dict:
    return next(panel for panel in _data_panels(dashboard) if panel["type"] == "table")


def _selectors(panel: dict) -> list[str]:
    return [column["selector"] for column in panel["targets"][0]["columns"]]


def _overrides(panel: dict) -> dict[str, list[dict]]:
    overrides = panel["fieldConfig"]["overrides"]
    return {override["matcher"]["options"]: override["properties"] for override in overrides}


def test_one_repository() -> None:
    """Scenario: One repository."""
    text, dashboard = _render(_KINOZAL)
    assert [entry["name"] for entry in dashboard["__inputs"]] == ["DS_INFINITY"]
    assert "uid" not in dashboard
    for token in ("grafanacloud-infinity", "__REPOSITORY__", f"{_OTHER}/task-readings"):
        assert token not in text
    panels = _data_panels(dashboard)
    assert len(panels) == 7
    for panel in panels:
        assert panel["datasource"]["uid"] == "${DS_INFINITY}"
        (target,) = panel["targets"]
        assert target["datasource"]["uid"] == "${DS_INFINITY}"
        assert target["url"] == _url(_KINOZAL)
        assert _computed(target)["repository"] == f"'{_KINOZAL}'"
    table = _table(dashboard)
    (target,) = table["targets"]
    assert _computed(target)["issue"] == "replace(task_id, 'issue-', '')"
    by_name = _overrides(table)
    links = next(prop["value"] for prop in by_name["task_id"] if prop["id"] == "links")
    assert [link["url"] for link in links] == [_LINK]
    assert {"id": "custom.hidden", "value": True} in by_name["issue"]


def test_hours_panel() -> None:
    """Scenario: Hours panel."""
    _, dashboard = _render(_KINOZAL)
    (panel,) = [panel for panel in _data_panels(dashboard) if "hours" in _selectors(panel)]
    assert "agent_hours" in _selectors(panel)
    by_name = _overrides(panel)
    names = {
        field: next(prop["value"] for prop in by_name[field] if prop["id"] == "displayName")
        for field in ("hours", "agent_hours")
    }
    assert names["hours"] != names["agent_hours"]
    organize = next(t for t in _table(dashboard)["transformations"] if t["id"] == "organize")
    index = organize["options"]["indexByName"]
    assert index["agent_hours"] == index["hours"] + 1


def test_rate_panels() -> None:
    """Scenario: Rate panels."""
    _, dashboard = _render(_KINOZAL)
    rates = {
        "compactions_per_100_requests": ("compactions * 100 / api_requests", ["compactions"]),
        "failed_denied_per_100_requests": (
            "(failed + denied) * 100 / api_requests",
            ["failed", "denied"],
        ),
    }
    for rate, (expression, raw) in rates.items():
        (panel,) = [p for p in _data_panels(dashboard) if rate in _computed(p["targets"][0])]
        assert _computed(panel["targets"][0])[rate] == expression
        assert {*raw, "api_requests"} <= set(_selectors(panel))
        transformations = {t["id"]: t["options"] for t in panel["transformations"]}
        window = next(
            t["options"]["window"]
            for t in panel["transformations"]
            if t["options"].get("mode") == "windowFunctions"
        )
        assert window["field"] == rate
        assert {"id": "displayName", "value": "per task"} in _overrides(panel)[rate]
        hidden = transformations["organize"]["excludeByName"]
        assert hidden == dict.fromkeys([*raw, "api_requests"], True)


def test_several_repositories() -> None:
    """Scenario: Several repositories."""
    _, dashboard = _render(_OTHER, _KINOZAL)
    for panel in _data_panels(dashboard):
        targets = panel["targets"]
        assert [target["refId"] for target in targets] == ["A", "B"]
        assert [target["url"] for target in targets] == [_url(_OTHER), _url(_KINOZAL)]
        assert [_computed(target)["repository"] for target in targets] == [
            f"'{_OTHER}'",
            f"'{_KINOZAL}'",
        ]
        assert panel["transformations"][0]["id"] == "merge"
    assert dashboard["title"] == f"Per-task delivery: {_OTHER}, {_KINOZAL}"


def test_repeated_repository() -> None:
    """Scenario: Repeated repository."""
    _, dashboard = _render(_OTHER, _KINOZAL, _OTHER.upper())
    for panel in _data_panels(dashboard):
        assert [target["url"] for target in panel["targets"]] == [_url(_OTHER), _url(_KINOZAL)]


@pytest.mark.parametrize(
    "args", [["kinozal_scraper"], ["a/b/c"], ["owner/"], ["owner/."], ["owner/.."], []]
)
def test_malformed_repository(args: list[str]) -> None:
    """Scenario: Malformed repository."""
    result = _run(args)
    assert (result.returncode, result.stdout) == (2, "")
    assert (args[0] if args else "usage") in result.stderr.lower()
