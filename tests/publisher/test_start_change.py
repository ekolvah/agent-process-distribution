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

from tests.publisher.delivery_fakes import NO_AREA, ROOT, SKILL_SCRIPTS, Gh, load_script

MOVED_SCRIPTS = {
    "activate_protection.py",
    "archive_change.py",
    "check_red.py",
    "create_tracking_issue.py",
    "init.py",
    "manual.py",
    "onboarding.py",
    "quality.py",
    "resolve_review_thread.py",
    "set_status.py",
    "start_change.py",
    "steps.py",
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
_START = [_CHANGE, "--planner", "Claude", "--implementer", "Claude"]
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
        config = load_script("init").render_config_block().encode("utf-8")
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
        create.main([_CHANGE, "--area", "Observability"], gh=gh, root=root)
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
        create.main([_CHANGE, "--area", "Observability"], gh=gh, root=root)
    assert exc.value.code == 2 and _creates(gh) == []
    err = capsys.readouterr().err
    for message in messages:
        assert message in err, message


def test_plan_without_a_prior_issue(tmp_path: Path) -> None:
    """Scenario: Plan without a prior issue — an approve with no problem reference creates
    the issue (#186: the reviewer had to cite an unrelated one)."""
    create = load_script("create_tracking_issue")
    root = _change(tmp_path, tasks=_GROUP0.format(token=_PLACEHOLDER))
    gh = Gh()
    create.main([_CHANGE, "--area", "Observability"], gh=gh, root=root)
    assert len(_creates(gh)) == 1


def test_addition_without_evidence(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Scenario: Addition without evidence — a review still carrying the removed `additions`
    key is refused by both scripts, naming it, and nothing is created."""
    review = _review()
    review["additions"] = []
    message = "Additional properties are not allowed ('additions'"

    start_change = load_script("start_change")
    root = _change(tmp_path / "a", tasks=_GROUP0.format(token="tracking issue 7"), review=review)
    gh = Gh()
    with pytest.raises(SystemExit) as exc:
        start_change.main(_START, gh=gh, root=root)
    assert exc.value.code == 2 and _develops(gh) == []
    assert message in capsys.readouterr().err

    create = load_script("create_tracking_issue")
    root = _change(tmp_path / "b", tasks=_GROUP0.format(token=_PLACEHOLDER), review=review)
    gh = Gh()
    with pytest.raises(SystemExit) as exc:
        create.main([_CHANGE, "--area", "Observability"], gh=gh, root=root)
    assert exc.value.code == 2 and _creates(gh) == []
    assert message in capsys.readouterr().err


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
        create.main([_CHANGE, "--area", "Observability"], gh=gh, root=root)
    assert exc.value.code == 2 and _creates(gh) == []
    assert "$.classes.length.result" in capsys.readouterr().err

    # The same finding under `rework` is a valid file: the verdict is what stops the run.
    review["verdict"] = "rework"
    root = _change(tmp_path / "c", tasks=_GROUP0.format(token=_PLACEHOLDER), review=review)
    gh = Gh()
    with pytest.raises(SystemExit) as exc:
        create.main([_CHANGE, "--area", "Observability"], gh=gh, root=root)
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
    gh = Gh(root=root)
    start_change.main(_START, gh=gh, root=root)
    assert _develops(gh) == [["gh", "issue", "develop", "7", "--name", _CHANGE]]

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
    gh = Gh(status="Planned", other_items=[("Other", "Todo")], root=root)
    start_change.main(_START, gh=gh, root=root)
    assert len(_develops(gh)) == 1


def test_tasks_of_a_new_change_start(tmp_path: Path) -> None:
    """Scenario: Tasks of a new change — on a Planned issue: the linked branch, In Progress,
    the provenance line, in that order; nothing asked."""
    start_change = load_script("start_change")
    root = _change(tmp_path, tasks=_GROUP0.format(token="tracking issue 7"))
    gh = Gh(status="Planned", root=root)

    start_change.main(_START, gh=gh, root=root)

    develop = _develops(gh)
    assert develop == [["gh", "issue", "develop", "7", "--name", _CHANGE]]
    fetch = ["git", "fetch", "origin", _CHANGE]
    add = [
        "git",
        "worktree",
        "add",
        "--track",
        "-b",
        _CHANGE,
        str(root / ".claude" / "worktrees" / _CHANGE),
        f"origin/{_CHANGE}",
    ]
    edits = gh.edits()
    assert len(edits) == 1
    assert edits[0][edits[0].index("--single-select-option-id") + 1] == "S_PROG"
    comments = [c for c in gh.calls if c[:3] == ["gh", "issue", "comment"]]
    assert comments == [
        ["gh", "issue", "comment", "7", "--body", "planner: Claude; implementer: Claude"]
    ]
    order = [
        gh.calls.index(develop[0]),
        gh.calls.index(fetch),
        gh.calls.index(add),
        gh.calls.index(edits[0]),
        gh.calls.index(comments[0]),
    ]
    assert order == sorted(order)


def test_codex_carrier_is_rejected(tmp_path: Path) -> None:
    """Scenario: Codex carrier — Claude is the only carrier; `Codex` for either role is a
    usage error before any GitHub call."""
    start_change = load_script("start_change")
    root = _change(tmp_path, tasks=_GROUP0.format(token="tracking issue 7"))
    for argv in (
        [_CHANGE, "--planner", "Codex", "--implementer", "Claude"],
        [_CHANGE, "--planner", "Claude", "--implementer", "Codex"],
    ):
        gh = Gh(status="Planned")
        with pytest.raises(SystemExit) as exc:
            start_change.main(argv, gh=gh, root=root)
        assert exc.value.code == 2, argv
        assert gh.calls == []


def test_interrupted_start_names_the_continuation(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A failure after the branch exists is exit 1 whose message names the steps left —
    `set_status.py 7 "In Progress"` and the `gh issue comment` — so the person completes
    them without a second `start_change` (PR 148, Codex P1)."""
    start_change = load_script("start_change")
    status_path = str(SKILL_SCRIPTS / "set_status.py")
    comment_cmd = 'gh issue comment 7 --body "planner: Claude; implementer: Claude"'

    root = _change(tmp_path / "a", tasks=_GROUP0.format(token="tracking issue 7"))
    gh = Gh(fail_on=["gh", "project", "item-edit"], root=root)
    with pytest.raises(SystemExit) as exc:
        start_change.main(_START, gh=gh, root=root)
    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert status_path in err and '7 "In Progress"' in err and comment_cmd in err

    root = _change(tmp_path / "b", tasks=_GROUP0.format(token="tracking issue 7"))
    gh = Gh(fail_on=["gh", "issue", "comment"], root=root)
    with pytest.raises(SystemExit) as exc:
        start_change.main(_START, gh=gh, root=root)
    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert comment_cmd in err and status_path not in err

    # `gh issue develop` can fail after it created the remote branch: the branch exists
    # (`git ls-remote --heads origin <change>` lists it) and the continuation starts with
    # the worktree steps, never `git switch` (PR 148, Codex P1, round 2; #236).
    switch_cmd = f"git switch {_CHANGE}"
    fetch_cmd = f"git fetch origin {_CHANGE}"
    root = _change(tmp_path / "c", tasks=_GROUP0.format(token="tracking issue 7"))
    gh = Gh(fail_on=["gh", "issue", "develop"], remote_branch=True, root=root)
    with pytest.raises(SystemExit) as exc:
        start_change.main(_START, gh=gh, root=root)
    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert switch_cmd not in err
    assert err.index(fetch_cmd) < err.index(status_path) < err.index(comment_cmd)
    assert gh.edits() == []

    root = _change(tmp_path / "d", tasks=_GROUP0.format(token="tracking issue 7"))
    gh = Gh(fail_on=["gh", "issue", "develop"], remote_branch=False, root=root)
    with pytest.raises(SystemExit) as exc:
        start_change.main(_START, gh=gh, root=root)
    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert "no branch" in err and fetch_cmd not in err and status_path not in err


def _run(cmd: list[str]) -> str:
    return load_script("set_status").run_gh(cmd)


def _git(*args: str) -> str:
    return _run(["git", *args])


def _clone(tmp_path: Path) -> Path:
    """A clone on `main` of a bare `origin` in `tmp_path`, with git's default fetch refspec:
    the release-recording config is committed, the fixture change is untracked."""
    origin, root = tmp_path / "origin.git", tmp_path / "root"
    _git("init", "--bare", "-b", "main", str(origin))
    _git("clone", "-q", str(origin), str(root))
    config = load_script("init").render_config_block().encode("utf-8")
    (root / "openspec").mkdir()
    (root / "openspec" / "config.yaml").write_bytes(config)
    _git("-C", str(root), "add", "openspec/config.yaml")
    _git("-C", str(root), "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "init")
    _git("-C", str(root), "push", "-q", "origin", "main")
    _change(root, tasks=_GROUP0.format(token="tracking issue 7"), config=config)
    return root


def _worktree(root: Path, branch: str) -> Path:
    path = root / ".claude" / "worktrees" / branch
    _git("-C", str(root), "worktree", "add", "-q", "-b", branch, str(path))
    return path


def _untracked(root: Path) -> set[str]:
    return set(_git("-C", str(root), "status", "--porcelain", "--untracked-files=all").splitlines())


def test_parallel_changes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Scenario: Parallel changes — the start of one change leaves the shared checkout on
    `main` with another change's files, and carries its own in a worktree tracking origin."""
    start_change = load_script("start_change")
    root = _clone(tmp_path)
    other = root / "openspec" / "changes" / "a"
    other.mkdir()
    (other / "proposal.md").write_text("## Why\n\nAnother change.\n", encoding="utf-8")
    monkeypatch.chdir(root)
    before = _untracked(root)

    start_change.main(_START, gh=Gh(root=root, git_runner=_run), root=root)

    after = _untracked(root)
    gone, new = before - after, after - before
    assert gone and all(line.startswith(f"?? openspec/changes/{_CHANGE}/") for line in gone)
    assert new and all(line.startswith("?? .claude/") for line in new)
    assert _git("-C", str(root), "branch", "--show-current").strip() == "main"
    assert (other / "proposal.md").is_file()
    assert not (root / "openspec" / "changes" / _CHANGE).exists()
    worktree = root / ".claude" / "worktrees" / _CHANGE
    assert (worktree / "openspec" / "changes" / _CHANGE / "tasks.md").is_file()
    upstream = _git("-C", str(worktree), "rev-parse", "--abbrev-ref", "@{u}")
    assert upstream.strip() == f"origin/{_CHANGE}"


def test_worktree_step_fails_after_branch_exists(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Scenario: Worktree step fails after the branch exists — exit 1 naming the steps left
    from the failed one, in order, and no `git switch`."""
    start_change = load_script("start_change")
    root = _change(tmp_path, tasks=_GROUP0.format(token="tracking issue 7"))
    gh = Gh(fail_on=["git", "worktree", "add"], remote_branch=True, root=root)

    with pytest.raises(SystemExit) as exc:
        start_change.main(_START, gh=gh, root=root)

    assert exc.value.code == 1
    err = capsys.readouterr().err
    status_path = str(SKILL_SCRIPTS / "set_status.py")
    rest = err[err.index("finish by hand") :]
    assert (
        rest.index("git worktree add")
        < rest.index("then move")
        < rest.index(f'{status_path}" 7 "In Progress"')
        < rest.index("gh issue comment 7")
    )
    assert "git switch" not in err
    assert gh.edits() == []


def test_merged_changes_worktree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Scenario: Merged change's worktree — a merged clean one is removed and printed, a merged
    dirty one kept and named, one with an open PR or none untouched; the start goes on."""
    start_change = load_script("start_change")
    root = _clone(tmp_path)
    done, dirty, open_, new = (_worktree(root, b) for b in ("done", "dirty", "open", "new"))
    (dirty / "notes.txt").write_text("uncommitted\n", encoding="utf-8")
    monkeypatch.chdir(root)
    gh = Gh(
        root=root,
        git_runner=_run,
        pr_states={"done": "MERGED", "dirty": "MERGED", "open": "OPEN"},
    )

    start_change.main(_START, gh=gh, root=root)

    out, err = capsys.readouterr()
    assert not done.exists()
    assert done.as_posix() not in _git("worktree", "list", "--porcelain")
    assert f"removed: {done}" in out
    assert dirty.exists() and open_.exists() and new.exists()
    assert f"kept: {dirty}" in err
    assert (root / ".claude" / "worktrees" / _CHANGE / "openspec" / "changes" / _CHANGE).is_dir()
    assert _git("branch", "--list", "done").strip()


def test_started_from_inside_the_previous_changes_worktree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Scenario: Started from inside the previous change's worktree — the new worktree is the
    main worktree's, and the one containing the cwd is neither removed nor examined."""
    start_change = load_script("start_change")
    main_root = _clone(tmp_path)
    prev = _worktree(main_root, "prev")
    _change(prev, tasks=_GROUP0.format(token="tracking issue 7"), config=None)
    monkeypatch.chdir(prev)
    gh = Gh(root=main_root, git_runner=_run, pr_states={"prev": "MERGED"})

    start_change.main(_START, gh=gh, root=prev)

    out, err = capsys.readouterr()
    worktree = main_root / ".claude" / "worktrees" / _CHANGE
    assert (worktree / "openspec" / "changes" / _CHANGE / "tasks.md").is_file()
    assert not (prev / ".claude").exists()
    assert prev.is_dir()
    assert str(prev) not in out and str(prev) not in err
    assert ["gh", "pr", "view", "prev", "--json", "state"] not in gh.calls


def test_cleanup_fails(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Scenario: Cleanup fails — a `kept:` line naming the worktree and the failure; the
    start still creates its branch and exits 0."""
    start_change = load_script("start_change")
    root = _change(tmp_path, tasks=_GROUP0.format(token="tracking issue 7"))
    gh = Gh(
        root=root,
        extra_worktrees=["done"],
        pr_states={"done": "MERGED"},
        fail_on=["git", "worktree", "remove"],
    )

    start_change.main(_START, gh=gh, root=root)

    err = capsys.readouterr().err
    kept = next(line for line in err.splitlines() if line.startswith("kept: "))
    assert str(root / ".claude" / "worktrees" / "done") in kept and "boom" in kept
    assert len(_develops(gh)) == 1


def test_worktree_listing_fails(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Scenario: Worktree listing fails — exit 1 naming the error before any branch exists."""
    start_change = load_script("start_change")
    root = _change(tmp_path, tasks=_GROUP0.format(token="tracking issue 7"))
    gh = Gh(root=root, fail_on=["git", "worktree", "list"])

    with pytest.raises(SystemExit) as exc:
        start_change.main(_START, gh=gh, root=root)

    assert exc.value.code == 1
    assert "git worktree list" in capsys.readouterr().err
    assert _develops(gh) == []


def test_plan_approved_creates_the_issue(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Scenario: Plan approved — the issue from proposal.md, Planned with the area, the
    number into tasks.md before `set_status`; the area is required on the placeholder."""
    create = load_script("create_tracking_issue")

    root = _change(tmp_path / "a", tasks=_GROUP0.format(token=_PLACEHOLDER))
    gh = Gh()
    with pytest.raises(SystemExit) as exc:
        create.main([_CHANGE], gh=gh, root=root)
    assert exc.value.code == 2 and _creates(gh) == []
    # The planner chooses the area itself: the refusal lists the Project's options.
    err = capsys.readouterr().err
    assert "area required" in err
    assert all(a in err for a in ("Observability", "Distribution", "Token efficiency"))

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
    create.main([_CHANGE, "--area", "Observability"], gh=gh, root=root)
    created = _creates(gh)
    assert len(created) == 1
    assert created[0][created[0].index("--title") + 1] == _CHANGE
    body_file = Path(created[0][created[0].index("--body-file") + 1])
    assert body_file == root / "openspec" / "changes" / _CHANGE / "proposal.md"
    tasks = (root / "openspec" / "changes" / _CHANGE / "tasks.md").read_text(encoding="utf-8")
    assert "tracking issue 7" in tasks and _PLACEHOLDER not in tasks
    edits = gh.edits()
    assert [e[e.index("--single-select-option-id") + 1] for e in edits] == ["S_PLAN", "A_OBS"]
    assert gh.calls.index(created[0]) < gh.calls.index(edits[0])
    assert "issues/7" in capsys.readouterr().out

    # `set_status` fails after the create: the number is already in tasks.md and the
    # message names the resume — a re-run must not create a second issue. A multi-word
    # area stays one argument of the resume command.
    root = _change(tmp_path / "d", tasks=_GROUP0.format(token=_PLACEHOLDER))
    gh = Gh(fail_on=["gh", "project", "item-edit"])
    with pytest.raises(SystemExit) as exc:
        create.main([_CHANGE, "--area", "Token efficiency"], gh=gh, root=root)
    assert exc.value.code == 1
    tasks = (root / "openspec" / "changes" / _CHANGE / "tasks.md").read_text(encoding="utf-8")
    assert "tracking issue 7" in tasks
    err = capsys.readouterr().err
    assert str(SKILL_SCRIPTS / "set_status.py") in err
    assert '7 Planned --area "Token efficiency"' in err


def test_existing_tracking_issue(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Scenario: Existing tracking issue — no create, an area refused, Planned alone."""
    create = load_script("create_tracking_issue")

    root = _change(tmp_path / "a", tasks=_GROUP0.format(token="tracking issue 7"))
    gh = Gh()
    with pytest.raises(SystemExit) as exc:
        create.main([_CHANGE, "--area", "Observability"], gh=gh, root=root)
    assert exc.value.code == 2 and gh.edits() == [] and _creates(gh) == []
    assert "area is set at creation" in capsys.readouterr().err

    root = _change(tmp_path / "b", tasks=_GROUP0.format(token="tracking issue 7"))
    gh = Gh()
    create.main([_CHANGE], gh=gh, root=root)
    assert _creates(gh) == []
    assert [e[e.index("--single-select-option-id") + 1] for e in gh.edits()] == ["S_PLAN"]


def test_area_field_drift_creates_no_issue(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Scenario: Area field drift — the area resolves against the Project before the issue is
    created: an unknown name or a board without `Area` is exit 2 and no issue exists."""
    create = load_script("create_tracking_issue")
    tasks_md = Path("openspec") / "changes" / _CHANGE / "tasks.md"

    root = _change(tmp_path / "a", tasks=_GROUP0.format(token=_PLACEHOLDER))
    gh = Gh()
    with pytest.raises(SystemExit) as exc:
        create.main([_CHANGE, "--area", "Urgent"], gh=gh, root=root)
    assert exc.value.code == 2 and _creates(gh) == [] and gh.edits() == []
    err = capsys.readouterr().err
    assert "Urgent" in err and "Observability" in err and "Distribution" in err
    assert _PLACEHOLDER in (root / tasks_md).read_text(encoding="utf-8")

    root = _change(tmp_path / "b", tasks=_GROUP0.format(token=_PLACEHOLDER))
    gh = Gh(fields=NO_AREA)
    with pytest.raises(SystemExit) as exc:
        create.main([_CHANGE, "--area", "Observability"], gh=gh, root=root)
    assert exc.value.code == 2 and _creates(gh) == [] and gh.edits() == []
    assert "no field 'Area'" in capsys.readouterr().err
    assert _PLACEHOLDER in (root / tasks_md).read_text(encoding="utf-8")


def _release_config(recorded: str | None) -> bytes:
    """A config block recording `recorded`; `None` drops the release line."""
    lines = load_script("init").render_config_block().splitlines()
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
_SKILL_FIX = "claude plugin update agent-process@agent-process-marketplace --scope"
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
        assert "#v" not in err
        assert "Codex" not in err


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
