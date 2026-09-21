"""Delivery scripts of the OpenSpec apply loop (changes v2-1a-delivery-scripts,
v2-2d-check-red-test, v2-2e-wait-for-pr-checks and v2-2f-start-change).

One test per scenario of the change's spec deltas that a script can prove; the
scenario name is the test name. Scripts are imported inside the tests so that a
missing script fails its own scenario instead of erroring the whole module at
collection (``check_red`` counts a collection error as "not RED").

``check_red`` is exercised at the ``subprocess.run`` boundary: a fake that records the
command it received, writes the fixture report at the ``--junitxml=`` argument and returns
a ``CompletedProcess``. pytest itself is not spawned in the suite; the delivery of the
change runs it live.
"""

from __future__ import annotations

import importlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
SKILL_SCRIPTS = ROOT / "skills" / "agent-process" / "scripts"
MOVED_SCRIPTS = {
    "archive_change.py",
    "check_red.py",
    "create_tracking_issue.py",
    "resolve_review_thread.py",
    "set_status.py",
    "start_change.py",
    "wait_for_pr.py",
}
_PROJECT = {"id": "PVT_1", "number": 4, "title": "Board", "resourcePath": "/users/owner/projects/4"}
_FIELDS = {
    "fields": [
        {
            "id": "F_STATUS",
            "name": "Status",
            "type": "ProjectV2SingleSelectField",
            "options": [
                {"id": "S_TODO", "name": "Todo"},
                {"id": "S_PLAN", "name": "Planned"},
                {"id": "S_PROG", "name": "In Progress"},
            ],
        },
        {
            "id": "F_PRIO",
            "name": "Priority",
            "type": "ProjectV2SingleSelectField",
            "options": [{"id": "P_HIGH", "name": "High"}, {"id": "P_LOW", "name": "Low"}],
        },
    ]
}


def _script(name: str) -> Any:
    path = SKILL_SCRIPTS / f"{name}.py"
    if path.is_file():
        module_name = f"agent_process_skill_{name}"
        if module_name in sys.modules:
            return sys.modules[module_name]
        spec = importlib.util.spec_from_file_location(module_name, path)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        sys.path.insert(0, str(SKILL_SCRIPTS))
        try:
            spec.loader.exec_module(module)
        finally:
            sys.path.remove(str(SKILL_SCRIPTS))
        return module
    return importlib.import_module(f"scripts.{name}")


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


class _Gh:
    """Fake `gh`: answers by command shape, records every call.

    `status` is what `gh issue view --json projectItems` reports for the issue on the
    linked Project (`None`: the issue is no item of it); `other_items` are the issue's items
    on other Projects, `(title, status)` each, listed first; `fail_on` is a command head
    that raises as `run_gh` does on a non-zero exit.
    """

    def __init__(
        self,
        *,
        projects: list[dict] | None = None,
        status: str | None = "Planned",
        other_items: list[tuple[str, str]] = (),
        fail_on: list[str] | None = None,
        remote_branch: bool = False,
    ) -> None:
        self.calls: list[list[str]] = []
        self.projects = [_PROJECT] if projects is None else projects
        self.status = status
        self.other_items = list(other_items)
        self.fail_on = fail_on
        self.remote_branch = remote_branch

    def __call__(self, cmd: list[str]) -> str:
        self.calls.append(cmd)
        head = cmd[:3]
        if self.fail_on is not None and cmd[: len(self.fail_on)] == self.fail_on:
            raise RuntimeError(f"`{' '.join(cmd)}` failed (rc=1): boom")
        if head == ["git", "ls-remote", "--heads"]:
            return f"0123abcd\trefs/heads/{cmd[-1]}\n" if self.remote_branch else ""
        if head == ["gh", "issue", "view"] and "projectItems" in cmd:
            # The shape `gh issue view 144 --json projectItems` printed: `title` is the
            # Project's title, one entry per Project the issue is an item of (v2-2f).
            items = [(t, s) for t, s in self.other_items]
            if self.status is not None:
                items.append((_PROJECT["title"], self.status))
            return json.dumps(
                {
                    "projectItems": [
                        {"status": {"optionId": "S_X", "name": s}, "title": t} for t, s in items
                    ]
                }
            )
        if head == ["gh", "issue", "develop"]:
            return "github.com/owner/repo/tree/branch\n"
        if head == ["gh", "issue", "comment"]:
            return "https://github.com/owner/repo/issues/7#issuecomment-1\n"
        if head == ["gh", "issue", "create"]:
            return "https://github.com/owner/repo/issues/7\n"
        if head == ["gh", "repo", "view"]:
            # `Nodes` with a capital N is what gh 2.87.3 prints for `--json projectsV2`.
            return json.dumps(
                {
                    "owner": {"login": "owner"},
                    "name": "repo",
                    "projectsV2": {"Nodes": self.projects},
                }
            )
        if head == ["gh", "issue", "view"]:
            return json.dumps({"url": "https://github.com/owner/repo/issues/7"})
        if head == ["gh", "api", "graphql"]:
            raise AssertionError("set_status must read the linked Project with gh repo view")
        if head == ["gh", "project", "field-list"]:
            return json.dumps(_FIELDS)
        if head == ["gh", "project", "item-add"]:
            return json.dumps({"id": "PVTI_7"})
        if head == ["gh", "project", "item-edit"]:
            return ""
        raise AssertionError(f"unexpected gh call: {cmd}")

    def edits(self) -> list[list[str]]:
        return [c for c in self.calls if c[:3] == ["gh", "project", "item-edit"]]


def _fake_pytest(
    monkeypatch: pytest.MonkeyPatch, report_xml: str, *, returncode: int = 1
) -> list[list[str]]:
    """Replace `subprocess.run` of `check_red` with a pytest that writes `report_xml` where
    `--junitxml=` says and exits `returncode`; returns the list the commands are recorded
    into."""
    check_red = _script("check_red")
    commands: list[list[str]] = []

    def run(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        commands.append(list(cmd))
        report = next(a for a in cmd if a.startswith("--junitxml="))[len("--junitxml=") :]
        Path(report).write_text(report_xml, encoding="utf-8")
        return subprocess.CompletedProcess(cmd, returncode, stdout="", stderr="stopping")

    monkeypatch.setattr(check_red.subprocess, "run", run)
    return commands


def test_behavioural_change(monkeypatch: pytest.MonkeyPatch) -> None:
    """Scenarios: Behavioural change, Runner given, Configuration that cuts the run —
    `check_red` runs `python -m pytest` of its own interpreter under its own configuration
    with its own report path and the node ids, and judges RED from that report; no runner
    argument exists."""
    check_red = _script("check_red")
    node = "tests/publisher/test_x.py::test_a"
    red = (
        '<testsuites><testsuite><testcase classname="tests.publisher.test_x" name="test_a">'
        '<failure message="boom"/></testcase></testsuite></testsuites>'
    )
    green = (
        '<testsuites><testsuite><testcase classname="tests.publisher.test_x" name="test_a"/>'
        "</testsuite></testsuites>"
    )

    commands = _fake_pytest(monkeypatch, red)
    check_red.main([node])

    (cmd,) = commands
    assert cmd[:3] == [sys.executable, "-m", "pytest"]
    assert "--tb=no" in cmd
    # The run is the script's configuration, not the project's: `--maxfail=0` cancels a
    # fail-fast `-x`/`--maxfail` from `addopts` (pytest's last `maxfail` wins);
    # `-p no:stepwise` makes `--stepwise` a usage error (rc 4, no report → exit 2); an
    # empty `cache_dir` of the script's own leaves `--lf`/`--ff`/`--nf` nothing to replay
    # while the `cache` fixture stays (`-p no:cacheprovider` took it away — PR 145,
    # round 9). The RED verdict needs every node id run (rounds 6–9).
    assert "--maxfail=0" in cmd
    assert "no:stepwise" in cmd and cmd[cmd.index("no:stepwise") - 1] == "-p"
    assert "no:cacheprovider" not in cmd
    (report,) = (a for a in cmd if a.startswith("--junitxml="))
    (cache_dir,) = (a for a in cmd if a.startswith("cache_dir="))
    assert cmd[cmd.index(cache_dir) - 1] == "-o"
    assert Path(cache_dir[len("cache_dir=") :]).parent == Path(report[len("--junitxml=") :]).parent
    assert cmd[-1] == node

    _fake_pytest(monkeypatch, green)
    with pytest.raises(SystemExit) as exc:
        check_red.main([node])
    assert exc.value.code == 1

    # No runner argument: `--test` was an input for a consumer that does not exist
    # (issue 112), and its failure modes cost three review rounds (PR 145).
    with pytest.raises(SystemExit) as exc:
        check_red.main(["--test", "python -m pytest", node])
    assert exc.value.code == 2


def test_runner_owns_the_selection(monkeypatch: pytest.MonkeyPatch) -> None:
    """The report is the runner's answer to the node ids it received: `check_red` judges
    every testcase in it and re-derives no selection of its own. A node id spelled `./` or
    as an absolute path, or a project whose `rootdir` differs, spells the classname its own
    way; a second interpreter of the node id would drop the test and report "no tests
    collected" (PR 145)."""
    check_red = _script("check_red")
    _fake_pytest(
        monkeypatch,
        '<testsuites><testsuite><testcase classname="tests.test_x" name="test_a">'
        '<failure message="boom"/></testcase></testsuite></testsuites>',
    )
    check_red.main(["sub/tests/test_x.py::test_a"])
    check_red.main(["./tests/test_x.py::test_a"])


@pytest.mark.parametrize("returncode", [2, 3, 4])
def test_interrupted_run_is_no_verdict(monkeypatch: pytest.MonkeyPatch, returncode: int) -> None:
    """Scenario: Configuration that cuts the run — pytest's exit code is the signal that the
    run reached the end: 0, 1 and 5 are complete runs; 2 (interrupted: `pytest.exit()` from a
    hook, `--stepwise`, Ctrl-C), 3 (internal error) and 4 (usage error) are not, and the
    report they leave — partial or absent — is no verdict (exit 2), never RED (PR 145,
    round 9)."""
    check_red = _script("check_red")
    red = (
        '<testsuites><testsuite><testcase classname="tests.test_x" name="test_a">'
        '<failure message="boom"/></testcase></testsuite></testsuites>'
    )
    _fake_pytest(monkeypatch, red, returncode=returncode)
    with pytest.raises(SystemExit) as exc:
        check_red.main(["tests/test_x.py::test_a", "tests/test_x.py::test_b"])
    assert exc.value.code == 2

    # 5 (no tests collected) is a complete run: the empty report is judged as such.
    _fake_pytest(monkeypatch, "<testsuites><testsuite/></testsuites>", returncode=5)
    with pytest.raises(SystemExit) as exc:
        check_red.main(["tests/test_x.py::test_a"])
    assert exc.value.code == 1


def test_tracking_issue_created() -> None:
    """Scenario: Tracking issue created — names resolve to ids, item-edit carries them."""
    set_status = _script("set_status")
    gh = _Gh()

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
    set_status = _script("set_status")
    gh = _Gh()

    with pytest.raises(SystemExit) as exc:
        set_status.main(["7", "In Progress", "--priority", "Urgent"], gh=gh)

    assert exc.value.code == 2
    assert gh.edits() == []
    err = capsys.readouterr().err
    assert "Urgent" in err and "High" in err and "Low" in err


def test_priority_only() -> None:
    """Scenario: Priority only — Status is optional; nothing given at all is a usage error."""
    set_status = _script("set_status")
    gh = _Gh()

    set_status.main(["7", "--priority", "High"], gh=gh)

    edits = gh.edits()
    assert len(edits) == 1
    assert edits[0][edits[0].index("--field-id") + 1] == "F_PRIO"
    assert edits[0][edits[0].index("--single-select-option-id") + 1] == "P_HIGH"

    gh = _Gh()
    with pytest.raises(SystemExit) as exc:
        set_status.main(["7"], gh=gh)
    assert exc.value.code == 2
    assert gh.edits() == []


def test_linked_project_of_another_owner() -> None:
    """The Project's owner comes from its resourcePath, not from the repository's owner."""
    set_status = _script("set_status")
    gh = _Gh(projects=[{**_PROJECT, "resourcePath": "/orgs/acme/projects/4"}])

    set_status.set_status(7, "In Progress", gh=gh)

    owners = [c[c.index("--owner") + 1] for c in gh.calls if "--owner" in c]
    assert owners and set(owners) == {"acme"}


def test_several_linked_projects(capsys: pytest.CaptureFixture[str]) -> None:
    """Scenario: Several linked Projects — zero or several linked Projects → exit 2 naming them."""
    set_status = _script("set_status")
    gh = _Gh(projects=[_PROJECT, {"id": "PVT_2", "number": 5, "title": "Other"}])

    with pytest.raises(SystemExit) as exc:
        set_status.main(["7", "In Progress"], gh=gh)

    assert exc.value.code == 2
    assert gh.edits() == []
    err = capsys.readouterr().err
    assert "#4 Board" in err and "#5 Other" in err

    gh = _Gh(projects=[])
    with pytest.raises(SystemExit) as exc:
        set_status.main(["7", "In Progress"], gh=gh)
    assert exc.value.code == 2
    assert gh.edits() == []


_CHANGE = "v2-9-example"
_START = [_CHANGE, "--planner", "Claude", "--implementer", "Codex"]
_PLACEHOLDER = "tracking issue <N>"
_GROUP0 = "- [ ] 0.1 `python skills/agent-process/scripts/start_change.py v2-9-example …` ({token})\n"


def _change(tmp_path: Path, *, verdict: str = "approve", tasks: str) -> Path:
    """A change directory under `tmp_path` with the three files the scripts read."""
    change_dir = tmp_path / "openspec" / "changes" / _CHANGE
    change_dir.mkdir(parents=True)
    (change_dir / "architect-review.md").write_text(
        f"## Verdict\n\n{verdict}\nreasoning\n\n## Findings\n\nnone\n", encoding="utf-8"
    )
    (change_dir / "tasks.md").write_text(tasks, encoding="utf-8")
    (change_dir / "proposal.md").write_text("## Why\n\nA fixture.\n", encoding="utf-8")
    return tmp_path


def _develops(gh: _Gh) -> list[list[str]]:
    return [c for c in gh.calls if c[:3] == ["gh", "issue", "develop"]]


def _creates(gh: _Gh) -> list[list[str]]:
    return [c for c in gh.calls if c[:3] == ["gh", "issue", "create"]]


def test_verdict_is_rework(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Scenario: Verdict is rework — exit 2 naming the rework, no branch."""
    start_change = _script("start_change")
    root = _change(tmp_path, verdict="rework", tasks=_GROUP0.format(token="tracking issue 7"))
    gh = _Gh()

    with pytest.raises(SystemExit) as exc:
        start_change.main(_START, gh=gh, root=root)

    assert exc.value.code == 2
    assert _develops(gh) == []
    assert "rework" in capsys.readouterr().err


def test_propose_run_stopped_before_its_tail(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Scenario: Propose run stopped before its tail — the placeholder token, a Status other
    than Planned or no Project item → `propose run not finished`, exit 2, no branch."""
    start_change = _script("start_change")
    line = "propose run not finished"

    root = _change(tmp_path / "a", tasks=_GROUP0.format(token=_PLACEHOLDER))
    gh = _Gh()
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
    gh = _Gh()
    start_change.main(_START, gh=gh, root=root)
    assert _develops(gh) == [["gh", "issue", "develop", "-c", "7", "--name", _CHANGE]]

    root = _change(
        tmp_path / "b2",
        tasks=_GROUP0.format(token=_PLACEHOLDER) + "- [ ] 1.1 fixture tracking issue 9\n",
    )
    gh = _Gh()
    with pytest.raises(SystemExit) as exc:
        start_change.main(_START, gh=gh, root=root)
    assert exc.value.code == 2 and _develops(gh) == []
    assert line in capsys.readouterr().err

    root = _change(tmp_path / "c", tasks=_GROUP0.format(token="tracking issue 7"))
    gh = _Gh(status="Todo")
    with pytest.raises(SystemExit) as exc:
        start_change.main(_START, gh=gh, root=root)
    assert exc.value.code == 2 and _develops(gh) == []
    err = capsys.readouterr().err
    assert line in err and "Todo" in err

    root = _change(tmp_path / "d", tasks=_GROUP0.format(token="tracking issue 7"))
    gh = _Gh(status=None)
    with pytest.raises(SystemExit) as exc:
        start_change.main(_START, gh=gh, root=root)
    assert exc.value.code == 2 and _develops(gh) == []
    err = capsys.readouterr().err
    assert line in err and "Status: none" in err

    # The Status read is the linked Project's, not the first item's: an unrelated board in
    # Planned does not start the delivery, one in Todo does not block it (PR 148, Codex P1).
    root = _change(tmp_path / "e", tasks=_GROUP0.format(token="tracking issue 7"))
    gh = _Gh(status=None, other_items=[("Other", "Planned")])
    with pytest.raises(SystemExit) as exc:
        start_change.main(_START, gh=gh, root=root)
    assert exc.value.code == 2 and _develops(gh) == []
    assert "Status: none" in capsys.readouterr().err

    root = _change(tmp_path / "f", tasks=_GROUP0.format(token="tracking issue 7"))
    gh = _Gh(status="Planned", other_items=[("Other", "Todo")])
    start_change.main(_START, gh=gh, root=root)
    assert len(_develops(gh)) == 1


def test_tasks_of_a_new_change_start(tmp_path: Path) -> None:
    """Scenario: Tasks of a new change — on a Planned issue: the linked branch, In Progress,
    the provenance line, in that order; nothing asked."""
    start_change = _script("start_change")
    root = _change(tmp_path, tasks=_GROUP0.format(token="tracking issue 7"))
    gh = _Gh(status="Planned")

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
    start_change = _script("start_change")
    status_path = str(SKILL_SCRIPTS / "set_status.py")
    comment_cmd = 'gh issue comment 7 --body "planner: Claude; implementer: Codex"'

    root = _change(tmp_path / "a", tasks=_GROUP0.format(token="tracking issue 7"))
    gh = _Gh(fail_on=["gh", "project", "item-edit"])
    with pytest.raises(SystemExit) as exc:
        start_change.main(_START, gh=gh, root=root)
    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert status_path in err and '7 "In Progress"' in err and comment_cmd in err

    root = _change(tmp_path / "b", tasks=_GROUP0.format(token="tracking issue 7"))
    gh = _Gh(fail_on=["gh", "issue", "comment"])
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
    gh = _Gh(fail_on=["gh", "issue", "develop"], remote_branch=True)
    with pytest.raises(SystemExit) as exc:
        start_change.main(_START, gh=gh, root=root)
    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert err.index(switch_cmd) < err.index(status_path) < err.index(comment_cmd)
    assert gh.edits() == []

    root = _change(tmp_path / "d", tasks=_GROUP0.format(token="tracking issue 7"))
    gh = _Gh(fail_on=["gh", "issue", "develop"], remote_branch=False)
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
    create = _script("create_tracking_issue")

    root = _change(tmp_path / "a", tasks=_GROUP0.format(token=_PLACEHOLDER))
    gh = _Gh()
    with pytest.raises(SystemExit) as exc:
        create.main([_CHANGE], gh=gh, root=root)
    assert exc.value.code == 2 and _creates(gh) == []
    assert "priority" in capsys.readouterr().err

    # The number in the token and the literal `<N>` elsewhere: the existing-issue branch.
    root = _change(
        tmp_path / "b",
        tasks=_GROUP0.format(token="tracking issue 7") + "- [ ] 1.1 asserts `<N>` in the rule\n",
    )
    gh = _Gh()
    create.main([_CHANGE], gh=gh, root=root)
    assert _creates(gh) == []
    assert [e[e.index("--single-select-option-id") + 1] for e in gh.edits()] == ["S_PLAN"]

    root = _change(tmp_path / "c", tasks=_GROUP0.format(token=_PLACEHOLDER))
    gh = _Gh()
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
    gh = _Gh(fail_on=["gh", "project", "item-edit"])
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
    create = _script("create_tracking_issue")

    root = _change(tmp_path / "a", tasks=_GROUP0.format(token="tracking issue 7"))
    gh = _Gh()
    with pytest.raises(SystemExit) as exc:
        create.main([_CHANGE, "--priority", "High"], gh=gh, root=root)
    assert exc.value.code == 2 and gh.edits() == [] and _creates(gh) == []
    assert "priority" in capsys.readouterr().err

    root = _change(tmp_path / "b", tasks=_GROUP0.format(token="tracking issue 7"))
    gh = _Gh()
    create.main([_CHANGE], gh=gh, root=root)
    assert _creates(gh) == []
    assert [e[e.index("--single-select-option-id") + 1] for e in gh.edits()] == ["S_PLAN"]


def _checks(*checks: tuple[str, str]) -> tuple[int, str, str]:
    """A `gh pr checks --json name,bucket,link` read: exit 0 whatever the buckets are."""
    rows = [{"name": n, "bucket": b, "link": f"https://ci.test/{n}"} for n, b in checks]
    return 0, json.dumps(rows), ""


# The rollup is empty for seconds after a push: gh reports it as an error, not as `[]`.
_EMPTY = (1, "", "no checks reported on the 'x' branch\n")
_PR_URL = "https://github.com/owner/repo/pull/9"


def _threads(*unresolved: str, head: str = "A") -> str:
    return json.dumps(
        {
            "data": {
                "repository": {
                    "pullRequest": {
                        "url": _PR_URL,
                        "headRefOid": head,
                        "reviewThreads": {
                            "pageInfo": {"hasNextPage": False},
                            "nodes": [
                                {
                                    "id": f"T_{i}",
                                    "isResolved": False,
                                    "path": path,
                                    "line": 1,
                                    "comments": {
                                        "nodes": [
                                            {
                                                "author": {"login": "reviewer"},
                                                "body": f"fix {path}",
                                                "url": f"https://github.com/t/{i}",
                                            }
                                        ]
                                    },
                                }
                                for i, path in enumerate(unresolved)
                            ],
                        },
                    }
                }
            }
        }
    )


class _Sequence:
    """Fake `gh` for `wait_for_pr`, a `CompletedProcess` per call: for `gh pr checks … --json`
    the next of the `(rc, stdout, stderr)` reads (the last one repeats), counted in `polls`;
    for `gh pr view … --json headRefOid` the next of `heads`; for the GraphQL query the
    next of the threads payloads (the last ones repeat)."""

    def __init__(
        self,
        reads: list[tuple[int, str, str]],
        threads: str | list[str],
        heads: list[str] | None = None,
    ) -> None:
        self.reads = list(reads)
        self.threads = [threads] if isinstance(threads, str) else list(threads)
        self.heads = list(heads or ["A"])
        self.polls = 0

    @staticmethod
    def _next(items: list[Any]) -> Any:
        return items.pop(0) if len(items) > 1 else items[0]

    def __call__(self, cmd: list[str]) -> subprocess.CompletedProcess[str]:
        if cmd[:3] == ["gh", "pr", "checks"]:
            assert "--json" in cmd and "--watch" not in cmd, cmd
            self.polls += 1
            rc, out, err = self._next(self.reads)
            return subprocess.CompletedProcess(cmd, rc, out, err)
        if cmd[:3] == ["gh", "pr", "view"]:
            assert "headRefOid" in cmd, cmd
            head = json.dumps({"headRefOid": self._next(self.heads)})
            return subprocess.CompletedProcess(cmd, 0, head, "")
        if cmd[:3] == ["gh", "repo", "view"]:
            repo = json.dumps({"owner": {"login": "owner"}, "name": "repo"})
            return subprocess.CompletedProcess(cmd, 0, repo, "")
        if cmd[:3] == ["gh", "api", "graphql"]:
            return subprocess.CompletedProcess(cmd, 0, self._next(self.threads), "")
        raise AssertionError(f"unexpected gh call: {cmd}")


def _wait(
    capsys: pytest.CaptureFixture[str],
    reads: list[tuple[int, str, str]],
    threads: str | list[str] = _threads(),
    *,
    heads: list[str] | None = None,
    timeout: int = 1800,
) -> tuple[int, str, _Sequence, list[float]]:
    """Run `wait_for_pr` on the fake `gh`; the fake `sleep` advances the fake `clock`."""
    wait_for_pr = _script("wait_for_pr")
    gh = _Sequence(reads, threads, heads)
    now = [0.0]
    sleeps: list[float] = []

    def sleep(seconds: float) -> None:
        sleeps.append(seconds)
        now[0] += seconds

    code = wait_for_pr.wait_for_pr(9, gh=gh, clock=lambda: now[0], sleep=sleep, timeout=timeout)
    return code, capsys.readouterr().out, gh, sleeps


def test_pending_review(capsys: pytest.CaptureFixture[str]) -> None:
    """Scenario: Pending review — a `pending` bucket is a pending review; `fail`, `cancel` or
    an unresolved thread → 1; clean → 0; timeout → 3 naming the check; a `gh` failure is an
    error, never a verdict."""
    wait_for_pr = _script("wait_for_pr")
    green, running = ("quality", "pass"), ("agent-review", "pending")
    red, cancelled, done = (
        ("agent-review", "fail"),
        ("agent-review", "cancel"),
        ("agent-review", "pass"),
    )

    code, out, gh, _ = _wait(capsys, [_checks(green, running), _checks(green, red)])
    assert code == 1 and "failed: agent-review" in out and gh.polls == 3

    code, out, _, _ = _wait(capsys, [_checks(green, cancelled)])
    assert code == 1 and "failed: agent-review" in out

    code, out, _, _ = _wait(capsys, [_checks(green, done)], _threads("docs/a.md"))
    assert code == 1 and "docs/a.md" in out

    code, out, gh, sleeps = _wait(capsys, [_checks(green, done)])
    assert code == 0 and "clean:" in out and _PR_URL in out
    # A concluded set is trusted once two reads 30 s apart agree on it: a workflow that
    # attaches late is never hidden behind a fast one that already passed, because a clean
    # verdict ends the delivery loop and no later read would see it (PR 147, round 2).
    assert gh.polls == 2 and sleeps == [30]
    code, out, gh, _ = _wait(
        capsys, [_checks(green), _checks(green, running), _checks(green, done)]
    )
    assert code == 0 and gh.polls == 4
    # The two reads must be of one head (PR 147, round 3): a push between them, each head
    # read while only its fast check had attached, agrees on the names and proves nothing.
    code, out, gh, _ = _wait(
        capsys,
        [_checks(green), _checks(green), _checks(green, running), _checks(green, done)],
        _threads(head="B"),
        heads=["A", "B"],
    )
    assert code == 0 and gh.polls == 5
    # A push after the last read: the threads answer names another head → read again on it.
    code, out, gh, _ = _wait(
        capsys, [_checks(green, done)], _threads(head="B"), heads=["A", "A", "B"]
    )
    assert code == 0 and gh.polls == 4 and "waiting: a push" in out

    code, out, _, sleeps = _wait(capsys, [_checks(green, running)], timeout=120)
    assert code == 3 and "timeout" in out.lower() and "agent-review" in out
    assert sleeps == [30, 30, 30, 30]

    # The timeout is the time that elapsed, not the number of whole poll intervals that fit
    # (PR 147, round 1): a timeout that is not a multiple of the interval is waited through,
    # the last sleep is the remainder, and the last read is at the deadline.
    code, out, gh, sleeps = _wait(capsys, [_checks(green, running)], timeout=31)
    assert code == 3 and sleeps == [30, 1] and gh.polls == 3
    code, out, gh, sleeps = _wait(capsys, [_checks(green, running)], timeout=10)
    assert code == 3 and sleeps == [10] and gh.polls == 2

    with pytest.raises(RuntimeError, match="401"):
        wait_for_pr.wait_for_pr(
            9,
            gh=_Sequence([(1, "", "HTTP 401")], _threads()),
            clock=lambda: 0.0,
            sleep=lambda s: None,
        )


def test_empty_rollup_after_push(capsys: pytest.CaptureFixture[str]) -> None:
    """Scenario: Empty rollup after a push — `no checks reported` is read again after one
    poll interval, never reported clean or failed; a rollup that never fills → 3."""
    green, done = ("quality", "pass"), ("agent-review", "pass")

    code, out, gh, sleeps = _wait(capsys, [_EMPTY, _checks(green, done)])
    assert code == 0 and sleeps == [30, 30] and gh.polls == 3

    code, out, _, _ = _wait(capsys, [_EMPTY], timeout=120)
    assert code == 3 and "no checks" in out.lower()


@pytest.mark.parametrize(
    ("script", "attr"),
    [("set_status", "run_gh"), ("wait_for_pr", "run_gh"), ("archive_change", "_runner")],
)
def test_none_capture_is_an_error(monkeypatch: pytest.MonkeyPatch, script: str, attr: str) -> None:
    """AGENTS.md: a `None` stdout or stderr is a broken capture, never an empty string."""
    module = _script(script)

    class _Completed:
        returncode = 0
        stdout = None
        stderr = None

    monkeypatch.setattr(module.subprocess, "run", lambda *a, **k: _Completed())
    runner = getattr(module, attr)
    if attr == "_runner":
        runner = runner(Path("."))
    with pytest.raises(RuntimeError, match="capture"):
        runner(["gh", "repo", "view"])


def test_archive_runner_reports_a_failed_command_whose_output_is_not_utf8() -> None:
    """A pre-push hook that writes a code-page byte still reaches the operator: the
    failure names the command and its output, not a broken capture (§IV)."""
    runner = _script("archive_change")._runner(Path("."))
    child = "import sys; sys.stderr.buffer.write(b'tests failed \\x97 see above\\n'); sys.exit(1)"

    with pytest.raises(RuntimeError, match=r"failed \(rc=1\).*tests failed"):
        runner([sys.executable, "-c", child])


def test_archive_commit(tmp_path: Path) -> None:
    """Scenarios: Archive commit, Stale archive lock."""
    archive_change = _script("archive_change")
    change = "v2-9-example"
    change_dir = tmp_path / "openspec" / "changes" / change
    change_dir.mkdir(parents=True)
    archive = tmp_path / "openspec" / "changes" / "archive"
    archive.mkdir()
    lock = archive / ".openspec-archive.lock"
    tasks = change_dir / "tasks.md"
    # The own task's command sits on a continuation line (as on #124's task 4.3).
    tasks.write_text(
        "- [x] 1.1 done\n"
        "- [ ] 4.1 `git status --short` empty;\n"
        f"  `python skills/agent-process/scripts/archive_change.py {change}` archives, commits, pushes.\n"
        "- [ ] 4.2 `gh pr create`; the person merges.\n",
        encoding="utf-8",
    )
    order: list[str] = []
    status = ""

    def run(cmd: list[str]) -> str:
        if "archive" in cmd:
            order.append("archive")
            text = tasks.read_text(encoding="utf-8")
            assert "- [x] 4.1" in text and "- [ ] 4.2" in text
            (archive / f"2026-01-01-{change}").mkdir()
            tasks.replace(archive / f"2026-01-01-{change}" / "tasks.md")
            lock.write_text("", encoding="utf-8")
            return ""
        if cmd[:2] == ["git", "commit"]:
            order.append("commit")
            assert not lock.exists()
            return ""
        if cmd[:2] == ["git", "push"]:
            order.append("push")
            return ""
        if cmd[:2] == ["git", "add"]:
            return ""
        if cmd[:2] == ["git", "status"]:
            return status
        raise AssertionError(f"unexpected call: {cmd}")

    # No review request and no wait: the PR does not exist yet when the archive lands.
    assert archive_change.archive_change(change, root=tmp_path, run=run) == 0
    assert order == ["archive", "commit", "push"]

    # Scenario: Stale archive lock — a lock left by an interrupted run stops the script.
    lock.write_text("", encoding="utf-8")
    order.clear()
    assert archive_change.archive_change(change, root=tmp_path, run=run) == 2
    assert order == []

    # Scenario: Archive commit — the worktree must be clean before the archive; a stray edit
    # would be left behind the pushed head, so the script stops instead of committing openspec/.
    lock.unlink()
    status = " M skills/agent-process/scripts/wait_for_pr.py\n"
    assert archive_change.archive_change(change, root=tmp_path, run=run) == 2
    assert order == []
