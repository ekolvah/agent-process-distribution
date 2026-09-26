"""``start_change`` and ``create_tracking_issue``, the entry scripts of the OpenSpec delivery
loop (changes v2-1a-delivery-scripts, v2-2f-start-change, release-drift-check).

One test per scenario of the change's spec deltas that a script can prove; the
scenario name is the test name. Scripts are imported inside the tests so that a
missing script fails its own scenario instead of erroring the whole module at
collection (``check_red`` counts a collection error as "not RED").
"""

from __future__ import annotations

import importlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest

from tests.publisher.delivery_fakes import ROOT, SKILL_SCRIPTS, Gh, load_script

MOVED_SCRIPTS = {
    "activate_protection.py",
    "archive_change.py",
    "check_red.py",
    "create_tracking_issue.py",
    "init.py",
    "resolve_review_thread.py",
    "set_status.py",
    "start_change.py",
    "wait_for_pr.py",
}


def test_moved_start_scripts_resolve_consumer_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Portable scripts live only in the skill and repository work targets invocation cwd."""
    assert {path.name for path in SKILL_SCRIPTS.glob("*.py")} == MOVED_SCRIPTS
    for name in MOVED_SCRIPTS:
        assert not (ROOT / ".agent-process" / "scripts" / name).exists()

    monkeypatch.chdir(tmp_path)
    path = SKILL_SCRIPTS / "start_change.py"
    spec = importlib.util.spec_from_file_location("consumer_start_change", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(SKILL_SCRIPTS))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(SKILL_SCRIPTS))
    assert module.ROOT == tmp_path
    assert 'SCRIPT_DIR / "set_status.py"' in path.read_text(encoding="utf-8")


_CHANGE = "v2-9-example"
_START = [_CHANGE, "--planner", "Claude", "--implementer", "Codex"]
_PLACEHOLDER = "tracking issue <N>"
_GROUP0 = (
    "- [ ] 0.1 `python skills/agent-process/scripts/start_change.py v2-9-example …` ({token})\n"
)


_CLASSES = ("simpler", "map", "red", "platform", "replaced", "catcher", "length", "bespoke")


def _review(verdict: str = "approve") -> dict[str, Any]:
    """A review valid against the skill's schema: every class checked and `ok`."""
    return {
        "verdict": verdict,
        "reviewer": "architect-reviewer",
        "reasoning": "r",
        "classes": {name: {"evidence": "read", "result": "ok"} for name in _CLASSES},
        "scenario_coverage": [],
        "additions": [],
    }


def _change(
    tmp_path: Path,
    *,
    verdict: str = "approve",
    tasks: str,
    review: dict[str, Any] | None = None,
    config: bytes | None = None,
) -> Path:
    """A change directory under `tmp_path` with the three files the scripts read, in a
    consumer whose `openspec/config.yaml` records the skill's release unless `config` is given."""
    change_dir = tmp_path / "openspec" / "changes" / _CHANGE
    change_dir.mkdir(parents=True)
    if config is None:
        config = load_script("init").render_config_block("t").encode("utf-8")
    (tmp_path / "openspec" / "config.yaml").write_bytes(config)
    (change_dir / "architect-review.json").write_text(
        json.dumps(review or _review(verdict)), encoding="utf-8"
    )
    (change_dir / "tasks.md").write_text(tasks, encoding="utf-8")
    (change_dir / "proposal.md").write_text("## Why\n\nA fixture.\n", encoding="utf-8")
    return tmp_path


def _develops(gh: Gh) -> list[list[str]]:
    return [c for c in gh.calls if c[:3] == ["gh", "issue", "develop"]]


def _creates(gh: Gh) -> list[list[str]]:
    return [c for c in gh.calls if c[:3] == ["gh", "issue", "create"]]


def test_verdict_is_rework(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Scenario: Verdict is rework — exit 2 naming the rework, no branch."""
    start_change = load_script("start_change")
    root = _change(tmp_path, verdict="rework", tasks=_GROUP0.format(token="tracking issue 7"))
    gh = Gh()

    with pytest.raises(SystemExit) as exc:
        start_change.main(_START, gh=gh, root=root)

    assert exc.value.code == 2
    assert _develops(gh) == []
    assert "rework" in capsys.readouterr().err

    # The propose tail refuses the same verdict: no issue from a plan still in rework.
    create = load_script("create_tracking_issue")
    root = _change(tmp_path / "tail", verdict="rework", tasks=_GROUP0.format(token=_PLACEHOLDER))
    gh = Gh()
    with pytest.raises(SystemExit) as exc:
        create.main([_CHANGE, "--priority", "High"], gh=gh, root=root)
    assert exc.value.code == 2 and _creates(gh) == []
    assert "rework" in capsys.readouterr().err


def test_review_not_valid(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Scenario: Review class without evidence — both scripts name each validation error and
    create nothing, on fixtures that would create when the file is valid."""
    review = _review()
    del review["classes"]["length"]
    review["classes"]["simpler"]["evidence"] = ""
    review["classes"]["map"]["result"] = "finding"
    messages = (
        "'length' is a required property",
        "should be non-empty",
        "'finding' is a required property",
    )

    start_change = load_script("start_change")
    root = _change(tmp_path / "a", tasks=_GROUP0.format(token="tracking issue 7"), review=review)
    gh = Gh()
    with pytest.raises(SystemExit) as exc:
        start_change.main(_START, gh=gh, root=root)
    assert exc.value.code == 2 and _develops(gh) == []
    err = capsys.readouterr().err
    for message in messages:
        assert message in err, message

    create = load_script("create_tracking_issue")
    root = _change(tmp_path / "b", tasks=_GROUP0.format(token=_PLACEHOLDER), review=review)
    gh = Gh()
    with pytest.raises(SystemExit) as exc:
        create.main([_CHANGE, "--priority", "High"], gh=gh, root=root)
    assert exc.value.code == 2 and _creates(gh) == []
    err = capsys.readouterr().err
    for message in messages:
        assert message in err, message


def _addition(**fields: str) -> dict[str, str]:
    entry = {"path": "check.py", "problem": "#113", "standard": "pytest-bdd", "why_not": "w"}
    return {**entry, **fields}


def test_addition_without_evidence(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Scenario: Addition without evidence — under `approve` both scripts refuse an addition
    without a problem reference or a standard, and create nothing."""
    start_change = load_script("start_change")
    create = load_script("create_tracking_issue")
    cases = {
        "problem-none": ({"problem": "none"}, "'none' does not match"),
        "problem-adr": ({"problem": "ADR 0027"}, "'ADR 0027' does not match"),
        "standard-none": ({"standard": "none"}, "'none' should not be valid under"),
        "standard-capital": ({"standard": "None"}, "'None' should not be valid under"),
        "standard-na": ({"standard": "N/A"}, "'N/A' should not be valid under"),
        "standard-dash": ({"standard": "-"}, "'-' should not be valid under"),
        "standard-padded": ({"standard": " n/a "}, "' n/a ' should not be valid under"),
        "absent": (None, "'additions' is a required property"),
    }
    for name, (fields, message) in cases.items():
        review = _review()
        if fields is None:
            del review["additions"]
        else:
            review["additions"] = [_addition(**fields)]

        root = _change(
            tmp_path / name / "a", tasks=_GROUP0.format(token="tracking issue 7"), review=review
        )
        gh = Gh()
        with pytest.raises(SystemExit) as exc:
            start_change.main(_START, gh=gh, root=root)
        assert exc.value.code == 2 and _develops(gh) == [], name
        assert message in capsys.readouterr().err, name

        root = _change(
            tmp_path / name / "b", tasks=_GROUP0.format(token=_PLACEHOLDER), review=review
        )
        gh = Gh()
        with pytest.raises(SystemExit) as exc:
            create.main([_CHANGE, "--priority", "High"], gh=gh, root=root)
        assert exc.value.code == 2 and _creates(gh) == [], name
        assert message in capsys.readouterr().err, name

    # An approve with a reference and a standard creates the issue.
    review = _review()
    review["additions"] = [_addition()]
    root = _change(tmp_path / "ok", tasks=_GROUP0.format(token=_PLACEHOLDER), review=review)
    gh = Gh()
    create.main([_CHANGE, "--priority", "High"], gh=gh, root=root)
    assert len(_creates(gh)) == 1

    # A rework records the gap as found: valid, refused only for being rework.
    review = _review("rework")
    review["additions"] = [_addition(problem="none")]
    root = _change(
        tmp_path / "rework", tasks=_GROUP0.format(token="tracking issue 7"), review=review
    )
    gh = Gh()
    with pytest.raises(SystemExit) as exc:
        start_change.main(_START, gh=gh, root=root)
    assert exc.value.code == 2 and _develops(gh) == []
    err = capsys.readouterr().err
    assert "rework" in err and "does not match" not in err


def test_review_approves_an_open_finding(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`approve` beside a class whose result is `finding` is invalid: an open finding is rework
    (PR 158, Codex P1)."""
    review = _review()
    review["classes"]["length"] = {
        "evidence": "the rule is 41 words, the test asserts 12",
        "result": "finding",
        "finding": {"principle": "§VII", "artifact": "tasks.md:5.1", "what": "w", "change": "c"},
    }

    start_change = load_script("start_change")
    root = _change(tmp_path / "a", tasks=_GROUP0.format(token="tracking issue 7"), review=review)
    gh = Gh()
    with pytest.raises(SystemExit) as exc:
        start_change.main(_START, gh=gh, root=root)
    assert exc.value.code == 2 and _develops(gh) == []
    assert "$.classes.length.result" in capsys.readouterr().err

    create = load_script("create_tracking_issue")
    root = _change(tmp_path / "b", tasks=_GROUP0.format(token=_PLACEHOLDER), review=review)
    gh = Gh()
    with pytest.raises(SystemExit) as exc:
        create.main([_CHANGE, "--priority", "High"], gh=gh, root=root)
    assert exc.value.code == 2 and _creates(gh) == []
    assert "$.classes.length.result" in capsys.readouterr().err

    # The same finding under `rework` is a valid file: the verdict is what stops the run.
    review["verdict"] = "rework"
    root = _change(tmp_path / "c", tasks=_GROUP0.format(token=_PLACEHOLDER), review=review)
    gh = Gh()
    with pytest.raises(SystemExit) as exc:
        create.main([_CHANGE, "--priority", "High"], gh=gh, root=root)
    assert exc.value.code == 2 and _creates(gh) == []
    err = capsys.readouterr().err
    assert "verdict: rework" in err and "$.classes" not in err


def test_review_validator_absent(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """No validator is a visible stop, not a pass."""
    start_change = load_script("start_change")
    root = _change(tmp_path, tasks=_GROUP0.format(token="tracking issue 7"))
    monkeypatch.setitem(sys.modules, "jsonschema", None)
    gh = Gh()
    with pytest.raises(SystemExit) as exc:
        start_change.main(_START, gh=gh, root=root)
    assert exc.value.code == 2 and _develops(gh) == []
    assert "architect review not validated" in capsys.readouterr().err


def test_propose_run_stopped_before_its_tail(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Scenario: Propose run stopped before its tail — the placeholder token, a Status other
    than Planned or no Project item → `propose run not finished`, exit 2, no branch."""
    start_change = load_script("start_change")
    line = "propose run not finished"

    root = _change(tmp_path / "a", tasks=_GROUP0.format(token=_PLACEHOLDER))
    gh = Gh()
    with pytest.raises(SystemExit) as exc:
        start_change.main(_START, gh=gh, root=root)
    assert exc.value.code == 2 and _develops(gh) == []
    assert line in capsys.readouterr().err

    # The first token decides (Group 0 comes first): the literal `<N>`, the whole token or
    # `tracking issue 9` in a later line — a test description, a quoted rule — is text
    # (PR 148, Codex P2).
    root = _change(
        tmp_path / "b",
        tasks=_GROUP0.format(token="tracking issue 7")
        + "- [ ] 1.1 asserts `<N>` and `tracking issue <N>` in the rule; fixture tracking issue 9\n",
    )
    gh = Gh()
    start_change.main(_START, gh=gh, root=root)
    assert _develops(gh) == [["gh", "issue", "develop", "-c", "7", "--name", _CHANGE]]

    root = _change(
        tmp_path / "b2",
        tasks=_GROUP0.format(token=_PLACEHOLDER) + "- [ ] 1.1 fixture tracking issue 9\n",
    )
    gh = Gh()
    with pytest.raises(SystemExit) as exc:
        start_change.main(_START, gh=gh, root=root)
    assert exc.value.code == 2 and _develops(gh) == []
    assert line in capsys.readouterr().err

    root = _change(tmp_path / "c", tasks=_GROUP0.format(token="tracking issue 7"))
    gh = Gh(status="Todo")
    with pytest.raises(SystemExit) as exc:
        start_change.main(_START, gh=gh, root=root)
    assert exc.value.code == 2 and _develops(gh) == []
    err = capsys.readouterr().err
    assert line in err and "Todo" in err

    root = _change(tmp_path / "d", tasks=_GROUP0.format(token="tracking issue 7"))
    gh = Gh(status=None)
    with pytest.raises(SystemExit) as exc:
        start_change.main(_START, gh=gh, root=root)
    assert exc.value.code == 2 and _develops(gh) == []
    err = capsys.readouterr().err
    assert line in err and "Status: none" in err

    # The Status read is the linked Project's, not the first item's: an unrelated board in
    # Planned does not start the delivery, one in Todo does not block it (PR 148, Codex P1).
    root = _change(tmp_path / "e", tasks=_GROUP0.format(token="tracking issue 7"))
    gh = Gh(status=None, other_items=[("Other", "Planned")])
    with pytest.raises(SystemExit) as exc:
        start_change.main(_START, gh=gh, root=root)
    assert exc.value.code == 2 and _develops(gh) == []
    assert "Status: none" in capsys.readouterr().err

    root = _change(tmp_path / "f", tasks=_GROUP0.format(token="tracking issue 7"))
    gh = Gh(status="Planned", other_items=[("Other", "Todo")])
    start_change.main(_START, gh=gh, root=root)
    assert len(_develops(gh)) == 1


def test_tasks_of_a_new_change_start(tmp_path: Path) -> None:
    """Scenario: Tasks of a new change — on a Planned issue: the linked branch, In Progress,
    the provenance line, in that order; nothing asked."""
    start_change = load_script("start_change")
    root = _change(tmp_path, tasks=_GROUP0.format(token="tracking issue 7"))
    gh = Gh(status="Planned")

    start_change.main(_START, gh=gh, root=root)

    develop = _develops(gh)
    assert develop == [["gh", "issue", "develop", "-c", "7", "--name", _CHANGE]]
    edits = gh.edits()
    assert len(edits) == 1
    assert edits[0][edits[0].index("--single-select-option-id") + 1] == "S_PROG"
    comments = [c for c in gh.calls if c[:3] == ["gh", "issue", "comment"]]
    assert comments == [
        ["gh", "issue", "comment", "7", "--body", "planner: Claude; implementer: Codex"]
    ]
    order = [gh.calls.index(develop[0]), gh.calls.index(edits[0]), gh.calls.index(comments[0])]
    assert order == sorted(order)


def test_interrupted_start_names_the_continuation(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A failure after the branch exists is exit 1 whose message names the steps left —
    `set_status.py 7 "In Progress"` and the `gh issue comment` — so the person completes
    them without a second `start_change` (PR 148, Codex P1)."""
    start_change = load_script("start_change")
    status_path = str(SKILL_SCRIPTS / "set_status.py")
    comment_cmd = 'gh issue comment 7 --body "planner: Claude; implementer: Codex"'

    root = _change(tmp_path / "a", tasks=_GROUP0.format(token="tracking issue 7"))
    gh = Gh(fail_on=["gh", "project", "item-edit"])
    with pytest.raises(SystemExit) as exc:
        start_change.main(_START, gh=gh, root=root)
    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert status_path in err and '7 "In Progress"' in err and comment_cmd in err

    root = _change(tmp_path / "b", tasks=_GROUP0.format(token="tracking issue 7"))
    gh = Gh(fail_on=["gh", "issue", "comment"])
    with pytest.raises(SystemExit) as exc:
        start_change.main(_START, gh=gh, root=root)
    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert comment_cmd in err and status_path not in err

    # `gh issue develop -c` creates the remote branch, then checks it out: when the
    # checkout fails the branch exists (`git ls-remote --heads origin <change>` lists it)
    # and the continuation starts with `git switch` (PR 148, Codex P1, round 2).
    switch_cmd = f"git switch {_CHANGE}"
    root = _change(tmp_path / "c", tasks=_GROUP0.format(token="tracking issue 7"))
    gh = Gh(fail_on=["gh", "issue", "develop"], remote_branch=True)
    with pytest.raises(SystemExit) as exc:
        start_change.main(_START, gh=gh, root=root)
    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert err.index(switch_cmd) < err.index(status_path) < err.index(comment_cmd)
    assert gh.edits() == []

    root = _change(tmp_path / "d", tasks=_GROUP0.format(token="tracking issue 7"))
    gh = Gh(fail_on=["gh", "issue", "develop"], remote_branch=False)
    with pytest.raises(SystemExit) as exc:
        start_change.main(_START, gh=gh, root=root)
    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert "no branch" in err and switch_cmd not in err and status_path not in err


def test_plan_approved_creates_the_issue(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Scenario: Plan approved — the issue from proposal.md, Planned with the priority, the
    number into tasks.md before `set_status`; the priority is required on the placeholder."""
    create = load_script("create_tracking_issue")

    root = _change(tmp_path / "a", tasks=_GROUP0.format(token=_PLACEHOLDER))
    gh = Gh()
    with pytest.raises(SystemExit) as exc:
        create.main([_CHANGE], gh=gh, root=root)
    assert exc.value.code == 2 and _creates(gh) == []
    assert "priority" in capsys.readouterr().err

    # The number in the token and the literal `<N>` elsewhere: the existing-issue branch.
    root = _change(
        tmp_path / "b",
        tasks=_GROUP0.format(token="tracking issue 7") + "- [ ] 1.1 asserts `<N>` in the rule\n",
    )
    gh = Gh()
    create.main([_CHANGE], gh=gh, root=root)
    assert _creates(gh) == []
    assert [e[e.index("--single-select-option-id") + 1] for e in gh.edits()] == ["S_PLAN"]

    root = _change(tmp_path / "c", tasks=_GROUP0.format(token=_PLACEHOLDER))
    gh = Gh()
    create.main([_CHANGE, "--priority", "High"], gh=gh, root=root)
    created = _creates(gh)
    assert len(created) == 1
    assert created[0][created[0].index("--title") + 1] == _CHANGE
    body_file = Path(created[0][created[0].index("--body-file") + 1])
    assert body_file == root / "openspec" / "changes" / _CHANGE / "proposal.md"
    tasks = (root / "openspec" / "changes" / _CHANGE / "tasks.md").read_text(encoding="utf-8")
    assert "tracking issue 7" in tasks and _PLACEHOLDER not in tasks
    edits = gh.edits()
    assert [e[e.index("--single-select-option-id") + 1] for e in edits] == ["S_PLAN", "P_HIGH"]
    assert gh.calls.index(created[0]) < gh.calls.index(edits[0])
    assert "issues/7" in capsys.readouterr().out

    # `set_status` fails after the create: the number is already in tasks.md and the
    # message names the resume — a re-run must not create a second issue.
    root = _change(tmp_path / "d", tasks=_GROUP0.format(token=_PLACEHOLDER))
    gh = Gh(fail_on=["gh", "project", "item-edit"])
    with pytest.raises(SystemExit) as exc:
        create.main([_CHANGE, "--priority", "High"], gh=gh, root=root)
    assert exc.value.code == 1
    tasks = (root / "openspec" / "changes" / _CHANGE / "tasks.md").read_text(encoding="utf-8")
    assert "tracking issue 7" in tasks
    err = capsys.readouterr().err
    assert str(SKILL_SCRIPTS / "set_status.py") in err
    assert "7 Planned --priority High" in err


def test_existing_tracking_issue(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Scenario: Existing tracking issue — no create, a priority refused, Planned alone."""
    create = load_script("create_tracking_issue")

    root = _change(tmp_path / "a", tasks=_GROUP0.format(token="tracking issue 7"))
    gh = Gh()
    with pytest.raises(SystemExit) as exc:
        create.main([_CHANGE, "--priority", "High"], gh=gh, root=root)
    assert exc.value.code == 2 and gh.edits() == [] and _creates(gh) == []
    assert "priority" in capsys.readouterr().err

    root = _change(tmp_path / "b", tasks=_GROUP0.format(token="tracking issue 7"))
    gh = Gh()
    create.main([_CHANGE], gh=gh, root=root)
    assert _creates(gh) == []
    assert [e[e.index("--single-select-option-id") + 1] for e in gh.edits()] == ["S_PLAN"]


def _release_config(recorded: str | None) -> bytes:
    """A config block recording `recorded`; `None` drops the release line."""
    lines = load_script("init").render_config_block("t").splitlines()
    kept = [line for line in lines if not line.startswith("# agent-process release: ")]
    assert len(kept) == len(lines) - 1, "the rendered block records no release"
    if recorded is not None:
        kept.insert(1, f"# agent-process release: {recorded}")
    return ("\n".join(kept) + "\n").encode("utf-8")


def _mixed_line_endings() -> bytes:
    """The skill's own release in a file `init` refuses to read: CRLF and LF mixed."""
    return b"schema: spec-driven\r\n" + _release_config(load_script("init").VERSION)


_SCRIPTS = {"start_change": _START, "create_tracking_issue": [_CHANGE]}
_INSTALL_FIX = "re-run Install"
_SKILL_FIX = "claude plugin update"
# case -> (config: a release to record, `None` for no release line, or a bytes factory;
#          the release the message names for the project; the fix it names)
_DRIFT: dict[str, tuple[Any, str, str]] = {
    "no-block": (lambda: b"schema: spec-driven\n", "none", _INSTALL_FIX),
    "no-line": (None, "none", _INSTALL_FIX),
    "unparsable": ("abc", "abc", _INSTALL_FIX),
    "older": ("0.0.1", "0.0.1", _INSTALL_FIX),
    "newer": ("99.0.0", "99.0.0", _SKILL_FIX),
    "mixed-line-endings": (_mixed_line_endings, "none", _INSTALL_FIX),
}


@pytest.mark.parametrize("script", sorted(_SCRIPTS))
@pytest.mark.parametrize("case", sorted(_DRIFT))
def test_release_drift(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], script: str, case: str
) -> None:
    """Scenario: Release drift — exit 2 before any GitHub call, naming both releases and the
    fix for that direction; the drift wins over a rework verdict (design: Placement)."""
    config, recorded, fix = _DRIFT[case]
    module = load_script(script)
    version = load_script("init").VERSION
    text = config() if callable(config) else _release_config(config)
    for verdict in ("approve", "rework"):
        root = _change(
            tmp_path / verdict,
            verdict=verdict,
            tasks=_GROUP0.format(token="tracking issue 7"),
            config=text,
        )
        gh = Gh(status="Planned")
        with pytest.raises(SystemExit) as exc:
            module.main(_SCRIPTS[script], gh=gh, root=root)
        err = capsys.readouterr().err
        assert exc.value.code == 2, err
        assert gh.calls == []
        assert "release drift" in err and "verdict" not in err
        assert f"project records {recorded}" in err and f"skill is {version}" in err
        assert fix in err


@pytest.mark.parametrize("script", sorted(_SCRIPTS))
def test_skill_behind_names_observed_path(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], script: str
) -> None:
    """Scenario: Skill behind the project — the fix names the observed Claude path (#184)
    and the Codex `--version`, never `/plugin marketplace update`."""
    recorded = "99.0.0"
    root = _change(
        tmp_path,
        verdict="approve",
        tasks=_GROUP0.format(token="tracking issue 7"),
        config=_release_config(recorded),
    )
    with pytest.raises(SystemExit) as exc:
        load_script(script).main(_SCRIPTS[script], gh=Gh(status="Planned"), root=root)
    err = capsys.readouterr().err
    assert exc.value.code == 2, err
    for token in (
        f'claude plugin marketplace add "ekolvah/agent-process-distribution#v{recorded}"',
        "outside any project",
        "~/.claude/settings.json",
        "claude plugin update agent-process@agent-process-marketplace",
        "--scope",
        f"--version {recorded}",
    ):
        assert token in err
    assert "/plugin marketplace update" not in err
    update = err.index("claude plugin update")
    assert err.index("~/.claude/settings.json") < err.index("restart") < update
    assert "restart" in err[update:]


def test_publisher_checkout_is_exempt(tmp_path: Path) -> None:
    """Scenario: Publisher checkout — the scripts of `<root>/skills/agent-process/scripts` skip
    the comparison; a copy anywhere else under the root is compared."""
    init = load_script("init")
    (tmp_path / "openspec").mkdir()
    (tmp_path / "openspec" / "config.yaml").write_bytes(b"schema: spec-driven\n")
    publisher = tmp_path / "skills" / "agent-process" / "scripts"
    scratch = tmp_path / "scratch" / "skills" / "agent-process" / "scripts"
    for path in (publisher, scratch):
        path.mkdir(parents=True)

    assert init.release_drift(tmp_path, publisher) is None
    message = init.release_drift(tmp_path, scratch)
    assert message is not None and "project records none" in message
