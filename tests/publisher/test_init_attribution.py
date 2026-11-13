"""The consumer's telemetry attribution: `init` writes `env.OTEL_RESOURCE_ATTRIBUTES` into
`.claude/settings.json`, or prints its `manual telemetry-attribution` row (change
init-asks-for-telemetry-attribution). The fixture repository and the runner are described in
`test_init.py`."""

from __future__ import annotations

import json
from typing import Any, Callable

import pytest

from tests.publisher.init_harness import (
    ATTRIBUTION,
    Sandbox,
    fresh_settings,
    install,
    load_init,
    project_settings,
    transitions,
    user_settings,
)


def _row(out: str) -> str:
    (row,) = [ln for ln in out.splitlines() if ln.startswith("manual telemetry-attribution: ")]
    return row


def _no_attribution_row(out: str) -> None:
    assert "manual telemetry-attribution" not in out, out


@pytest.mark.parametrize(
    "seed",
    [None, {"env": {"KEEP": "1"}, "permissions": {}}, fresh_settings()],
    ids=["absent", "other-keys", "installed"],
)
def test_attribution_is_written(
    sandbox: Sandbox, capfd: pytest.CaptureFixture[str], seed: dict[str, Any] | None
) -> None:
    """Scenario: Attribution written."""
    path = sandbox.root / ".claude" / "settings.json"
    before = None if seed is None else project_settings(sandbox, seed).read_text("utf-8")
    init = load_init()
    assert install(init, sandbox, "--dry-run") == 0
    _no_attribution_row(capfd.readouterr().out)
    assert (path.read_text("utf-8") if path.exists() else None) == before
    assert install(init, sandbox, "--confirm") == 0
    _no_attribution_row(capfd.readouterr().out)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data.get("env", {}).get("OTEL_RESOURCE_ATTRIBUTES") == ATTRIBUTION, data
    for key, value in (seed or {}).items():
        expected = {**value, "OTEL_RESOURCE_ATTRIBUTES": ATTRIBUTION} if key == "env" else value
        assert data[key] == expected, data
    assert install(init, sandbox, "--confirm") == 0
    out = capfd.readouterr().out
    _no_attribution_row(out)
    assert transitions(out)["settings"] == "unchanged", out


def _machine_env(sb: Sandbox, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OTEL_RESOURCE_ATTRIBUTES", "team=media")


def _machine_settings(sb: Sandbox, monkeypatch: pytest.MonkeyPatch) -> None:
    user_settings(sb, json.dumps({"env": {"OTEL_RESOURCE_ATTRIBUTES": "team=media"}}))


@pytest.mark.parametrize("arrange", [_machine_env, _machine_settings], ids=["env", "user"])
def test_machine_attribution_is_kept(
    sandbox: Sandbox,
    capfd: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    arrange: Callable[[Sandbox, pytest.MonkeyPatch], None],
) -> None:
    """Scenario: Machine attribution kept."""
    arrange(sandbox, monkeypatch)
    init = load_init()
    assert install(init, sandbox, "--confirm") == 0
    data = json.loads((sandbox.root / ".claude" / "settings.json").read_text(encoding="utf-8"))
    assert "env" not in data, data
    row = _row(capfd.readouterr().out)
    for named in (ATTRIBUTION, "replaces", "team=media"):
        assert named in row, row


def test_other_repository_attribution_is_manual(
    sandbox: Sandbox, capfd: pytest.CaptureFixture[str]
) -> None:
    """Scenario: Another repository's attribution."""
    other = "vcs.repository.name=other/repo"
    path = project_settings(sandbox, {"env": {"OTEL_RESOURCE_ATTRIBUTES": other}})
    init = load_init()
    assert install(init, sandbox, "--confirm") == 0
    assert json.loads(path.read_text(encoding="utf-8"))["env"]["OTEL_RESOURCE_ATTRIBUTES"] == other
    row = _row(capfd.readouterr().out)
    assert ATTRIBUTION in row and "(cannot read: " not in row, row


def test_hand_formatted_settings_is_manual(
    sandbox: Sandbox, capfd: pytest.CaptureFixture[str]
) -> None:
    """Scenario: Settings in another form — the `settings` step stays unchanged."""
    data = {**fresh_settings(), "model": "opus"}
    project_settings(sandbox, data, text=json.dumps(data, indent=4))
    init = load_init()
    assert install(init, sandbox, "--dry-run") == 0
    out = capfd.readouterr().out
    assert transitions(out)["settings"] == "unchanged", out
    row = _row(out)
    assert "not in the form init writes" in row, row


def test_malformed_project_settings_is_printed(
    sandbox: Sandbox, capfd: pytest.CaptureFixture[str]
) -> None:
    """Scenario: Unreadable state — a file that is not JSON is a `settings` conflict, so the
    run exits 2 as it would without the row."""
    project_settings(sandbox, None, text="not json")
    init = load_init()
    assert install(init, sandbox, "--dry-run") == 2
    row = _row(capfd.readouterr().out)
    assert "(cannot read: " in row, row
