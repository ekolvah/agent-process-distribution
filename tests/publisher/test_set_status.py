"""``set_status`` of the OpenSpec delivery loop (change v2-1a-delivery-scripts).

One test per scenario of the change's spec deltas that a script can prove; the
scenario name is the test name. Scripts are imported inside the tests so that a
missing script fails its own scenario instead of erroring the whole module at
collection (``check_red`` counts a collection error as "not RED").
"""

from __future__ import annotations

import pytest

from tests.publisher.delivery_fakes import PROJECT, Gh, load_script


def test_tracking_issue_created() -> None:
    """Scenario: Tracking issue created — names resolve to ids, item-edit carries them."""
    set_status = load_script("set_status")
    gh = Gh()

    set_status.set_status(7, "In Progress", priority="High", gh=gh)

    edits = gh.edits()
    assert len(edits) == 2
    for cmd, field_id, option_id in zip(edits, ["F_STATUS", "F_PRIO"], ["S_PROG", "P_HIGH"]):
        assert cmd[cmd.index("--id") + 1] == "PVTI_7"
        assert cmd[cmd.index("--field-id") + 1] == field_id
        assert cmd[cmd.index("--project-id") + 1] == "PVT_1"
        assert cmd[cmd.index("--single-select-option-id") + 1] == option_id
    assert not any(c[:2] == ["gh", "api"] for c in gh.calls)


def test_priority_field_drift(capsys: pytest.CaptureFixture[str]) -> None:
    """Scenario: Priority field drift — unknown option → exit 2 listing the options, nothing changed."""
    set_status = load_script("set_status")
    gh = Gh()

    with pytest.raises(SystemExit) as exc:
        set_status.main(["7", "In Progress", "--priority", "Urgent"], gh=gh)

    assert exc.value.code == 2
    assert gh.edits() == []
    err = capsys.readouterr().err
    assert "Urgent" in err and "High" in err and "Low" in err


def test_priority_only() -> None:
    """Scenario: Priority only — Status is optional; nothing given at all is a usage error."""
    set_status = load_script("set_status")
    gh = Gh()

    set_status.main(["7", "--priority", "High"], gh=gh)

    edits = gh.edits()
    assert len(edits) == 1
    assert edits[0][edits[0].index("--field-id") + 1] == "F_PRIO"
    assert edits[0][edits[0].index("--single-select-option-id") + 1] == "P_HIGH"

    gh = Gh()
    with pytest.raises(SystemExit) as exc:
        set_status.main(["7"], gh=gh)
    assert exc.value.code == 2
    assert gh.edits() == []


def test_linked_project_of_another_owner() -> None:
    """The Project's owner comes from its resourcePath, not from the repository's owner."""
    set_status = load_script("set_status")
    gh = Gh(projects=[{**PROJECT, "resourcePath": "/orgs/acme/projects/4"}])

    set_status.set_status(7, "In Progress", gh=gh)

    owners = [c[c.index("--owner") + 1] for c in gh.calls if "--owner" in c]
    assert owners and set(owners) == {"acme"}


def test_several_linked_projects(capsys: pytest.CaptureFixture[str]) -> None:
    """Scenario: Several linked Projects — zero or several linked Projects → exit 2 naming them."""
    set_status = load_script("set_status")
    gh = Gh(projects=[PROJECT, {"id": "PVT_2", "number": 5, "title": "Other"}])

    with pytest.raises(SystemExit) as exc:
        set_status.main(["7", "In Progress"], gh=gh)

    assert exc.value.code == 2
    assert gh.edits() == []
    err = capsys.readouterr().err
    assert "#4 Board" in err and "#5 Other" in err

    gh = Gh(projects=[])
    with pytest.raises(SystemExit) as exc:
        set_status.main(["7", "In Progress"], gh=gh)
    assert exc.value.code == 2
    assert gh.edits() == []
