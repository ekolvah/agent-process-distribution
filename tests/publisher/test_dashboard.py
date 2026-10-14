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
    overrides = table["fieldConfig"]["overrides"]
    by_name = {override["matcher"]["options"]: override["properties"] for override in overrides}
    links = next(prop["value"] for prop in by_name["task_id"] if prop["id"] == "links")
    assert [link["url"] for link in links] == [_LINK]
    assert {"id": "custom.hidden", "value": True} in by_name["issue"]


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


@pytest.mark.parametrize("args", [["kinozal_scraper"], ["a/b/c"], ["owner/"], []])
def test_malformed_repository(args: list[str]) -> None:
    """Scenario: Malformed repository."""
    result = _run(args)
    assert (result.returncode, result.stdout) == (2, "")
    assert (args[0] if args else "usage") in result.stderr.lower()
