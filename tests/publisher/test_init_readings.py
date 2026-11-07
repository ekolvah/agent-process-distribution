"""Requirement *Task readings are set up, or printed with the reason* (change
task-readings-auto-setup): from the machine's `grafana` MCP server config `init` sets the
`GRAFANA_URL` variable, the `GRAFANA_SERVICE_ACCOUNT_TOKEN` secret and the per-task dashboard,
and prints the `manual task-readings` row only for what it could not set up, with the reason."""

from __future__ import annotations

import json
import re
from pathlib import Path
from types import ModuleType

import pytest

from tests.publisher.init_harness import (
    GRAFANA,
    HOST,
    OWNER,
    PACKAGE,
    REPO_NAME,
    FakeGrafana,
    Runner,
    Sandbox,
    grafana_config,
    install,
    load_init,
    transitions,
)

CONSUMER = f"{OWNER}/{REPO_NAME}"
TOKEN = "glsa_readings-token-0123456789"  # pragma: allowlist secret
OTHER = "https://other.grafana.net"
ROW = "manual task-readings: "
STEPS = ("task-readings-url", "task-readings-token", "task-readings-dashboard")
TEMPLATE = PACKAGE / "templates" / "per-task-dashboard.json"
TITLE = f"{json.loads(TEMPLATE.read_text(encoding='utf-8'))['title']}: {CONSUMER}"


def _setup(sb: Sandbox) -> tuple[ModuleType, Runner, FakeGrafana]:
    init = load_init()
    sb.grafana = FakeGrafana(init.manual.Unreadable)
    return init, Runner(init, HOST, sb.github), sb.grafana


def _rows(out: str) -> list[str]:
    return [ln for ln in out.splitlines() if ln.startswith(ROW)]


def _line(out: str, label: str) -> str:
    """The last transition line of `label`."""
    return [ln for ln in out.splitlines() if re.match(rf"[a-z]+ {label}: ", ln)][-1]


def _writes(runner: Runner) -> list[list[str]]:
    return [*runner.gh("variable", "set"), *runner.gh("secret", "set")]


def _no_token(runner: Runner, *streams: str) -> None:
    for text in streams:
        assert TOKEN not in text
    for cmd in runner.log:
        assert not [part for part in cmd if TOKEN in part], cmd


def test_setup_planned_from_mcp_config(sandbox: Sandbox, capfd: pytest.CaptureFixture[str]) -> None:
    """Scenario: Setup planned from the MCP config."""
    grafana_config(sandbox.home, token=TOKEN)
    init, runner, grafana = _setup(sandbox)
    assert install(init, sandbox, "--dry-run", runner=runner) == 0
    out, err = capfd.readouterr()
    assert {label: transitions(out).get(label) for label in STEPS} == dict.fromkeys(
        STEPS, "planned"
    ), out
    assert GRAFANA in _line(out, "task-readings-url")
    assert "infinity-uid" in _line(out, "task-readings-dashboard")
    assert _writes(runner) == [] and grafana.posted == []
    assert _rows(out) == [], out
    _no_token(runner, out, err)


@pytest.mark.parametrize("form", ["inline", "file"])
def test_setup_performed(
    sandbox: Sandbox, capfd: pytest.CaptureFixture[str], tmp_path: Path, form: str
) -> None:
    """Scenario: Setup performed."""
    if form == "inline":
        grafana_config(sandbox.home, token=TOKEN)
    else:
        token_file = tmp_path / "grafana-token"
        token_file.write_text(TOKEN + "\n", encoding="utf-8")
        grafana_config(sandbox.home, token_file=token_file)
    init, runner, grafana = _setup(sandbox)
    assert install(init, sandbox, "--confirm", runner=runner) == 0
    out, err = capfd.readouterr()
    assert sandbox.github.variables["GRAFANA_URL"] == GRAFANA
    assert sandbox.github.secret_values == {"GRAFANA_SERVICE_ACCOUNT_TOKEN": TOKEN}
    assert set(grafana.opened) == {(GRAFANA, TOKEN)}
    (posted,) = grafana.posted
    text = json.dumps(posted)
    assert "${DS_INFINITY}" not in text and '"uid": "infinity-uid"' in text, text
    assert posted["title"] == TITLE
    assert {label: transitions(out).get(label) for label in STEPS} == dict.fromkeys(
        STEPS, "written"
    ), out
    assert f"{GRAFANA}/d/new/per-task-delivery" in out
    assert _rows(out) == [], out
    _no_token(runner, out, err)


def test_setup_observed(sandbox: Sandbox, capfd: pytest.CaptureFixture[str]) -> None:
    """Scenario: Setup observed."""
    grafana_config(sandbox.home, token=TOKEN)
    sandbox.github.variables["GRAFANA_URL"] = GRAFANA
    sandbox.github.secrets.add("GRAFANA_SERVICE_ACCOUNT_TOKEN")
    init, runner, grafana = _setup(sandbox)
    # A substring of the search query: only the exact title is this repository's dashboard.
    grafana.titles = [f"{TITLE}-two", TITLE]
    assert install(init, sandbox, "--confirm", runner=runner) == 0
    out = capfd.readouterr().out
    assert {label: transitions(out).get(label) for label in STEPS} == dict.fromkeys(
        STEPS, "unchanged"
    ), out
    assert _writes(runner) == [] and grafana.posted == []
    assert _rows(out) == [], out


@pytest.mark.parametrize("case", ["another-stack", "no-infinity", "datasources-401"])
def test_setup_not_possible(sandbox: Sandbox, capfd: pytest.CaptureFixture[str], case: str) -> None:
    """Scenario: Setup not possible."""
    grafana_config(sandbox.home, token=TOKEN)
    init, runner, grafana = _setup(sandbox)
    if case == "another-stack":
        sandbox.github.variables["GRAFANA_URL"] = OTHER
    elif case == "no-infinity":
        grafana.sources = grafana.sources[:1]
    else:
        grafana.faults["datasources"] = "GET /api/datasources: HTTP 401: Unauthorized"
    assert install(init, sandbox, "--dry-run", runner=runner) == 0
    out, err = capfd.readouterr()
    labels = transitions(out)
    assert "task-readings-dashboard" not in labels, out
    (row,) = _rows(out)
    if case == "another-stack":
        assert not [label for label in STEPS if label in labels], out
        assert grafana.opened == [] and grafana.log == []
        assert row.endswith(f"(another stack: {OTHER})"), row
    elif case == "no-infinity":
        assert row.endswith(f"(not found: Infinity datasource in {GRAFANA})"), row
    else:
        assert "(cannot read: " in row and "401" in row and row.endswith(")"), row
    assert _writes(runner) == []
    _no_token(runner, out, err)


def test_another_stack_already_set(sandbox: Sandbox, capfd: pytest.CaptureFixture[str]) -> None:
    """Scenario: Another stack already set. No Grafana is injected: none may be opened."""
    grafana_config(sandbox.home, token=TOKEN)
    sandbox.github.variables["GRAFANA_URL"] = OTHER
    sandbox.github.secrets.add("GRAFANA_SERVICE_ACCOUNT_TOKEN")
    init = load_init()
    assert install(init, sandbox, "--dry-run") == 0
    out = capfd.readouterr().out
    assert not [label for label in STEPS if label in transitions(out)], out
    assert _rows(out) == [], out


@pytest.mark.parametrize("fault", ["secret-set", "post-403"])
def test_setup_write_fails(sandbox: Sandbox, capfd: pytest.CaptureFixture[str], fault: str) -> None:
    """Scenario: Setup write fails."""
    grafana_config(sandbox.home, token=TOKEN)
    init, runner, grafana = _setup(sandbox)
    if fault == "secret-set":
        sandbox.github.faults["secret-set"] = "fail"
        step, failure = "task-readings-token", "HTTP 422"
    else:
        grafana.faults["post"] = "POST /api/dashboards/db: HTTP 403: Permissions needed"
        step, failure = "task-readings-dashboard", "HTTP 403"
    assert install(init, sandbox, "--confirm", runner=runner) == 1
    out, err = capfd.readouterr()
    (error,) = [ln for ln in err.splitlines() if ln.startswith("error: ")]
    assert step in error and failure in error, err
    _no_token(runner, out, err)


def test_empty_token_file_is_not_found(
    sandbox: Sandbox, capfd: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """Scenario: Setup not possible — an empty token file is no token: no step, the row names
    the file."""
    token_file = tmp_path / "grafana-token"
    token_file.write_text(" \n", encoding="utf-8")
    grafana_config(sandbox.home, token_file=token_file)
    init, runner, grafana = _setup(sandbox)
    assert install(init, sandbox, "--dry-run", runner=runner) == 0
    out = capfd.readouterr().out
    assert not [label for label in STEPS if label in transitions(out)], out
    (row,) = _rows(out)
    assert row.endswith(f"(not found: {token_file})"), row
    assert grafana.opened == []
