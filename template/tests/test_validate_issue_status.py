"""Status-transition contract for a successfully planned issue."""

from __future__ import annotations

import pytest

import scripts.validate_issue_sections as validate_issue_sections


def test_planned_status_failure_stops_planner_handoff(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def fail_status(issue_number: int, status: str) -> None:
        assert (issue_number, status) == (519, "planned")
        raise RuntimeError("gh project item-edit failed")

    monkeypatch.setattr(
        validate_issue_sections.set_issue_status, "set_status", fail_status
    )

    with pytest.raises(SystemExit) as exc:
        validate_issue_sections._mark_planned(519)

    assert exc.value.code == 2
    assert "Planner hand-off stopped" in capsys.readouterr().err
