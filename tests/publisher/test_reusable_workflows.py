"""Contracts of the source repository's referenced GitHub workflows."""

from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

from scripts import head_review

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"


def _workflow(name: str) -> dict[Any, Any]:
    return yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8"))


def _trigger(document: dict[Any, Any]) -> Any:
    return document.get("on", document.get(True))


def test_callees_declare_workflow_call_without_pull_request_trigger() -> None:
    for name in (
        "reusable-agent-review.yml",
        "quality.yml",
    ):
        trigger = _trigger(_workflow(name))
        assert "workflow_call" in trigger
        assert "pull_request" not in trigger


def test_callee_schema_matches_local_callers_in_both_directions() -> None:
    pairs = (
        (
            "agent-review.yml",
            "agent-review",
            "reusable-agent-review.yml",
            "agent-review",
        ),
        ("agent-process.yml", "agent-process", "quality.yml", "quality"),
    )
    for caller_file, caller_job, callee_file, callee_job in pairs:
        caller = _workflow(caller_file)["jobs"][caller_job]
        schema = _trigger(_workflow(callee_file))["workflow_call"] or {}
        inputs = schema.get("inputs", {})
        secrets = schema.get("secrets", {})
        assert set(caller.get("with", {})) == set(inputs)
        assert set(caller.get("secrets", {})) == set(secrets)
        assert all(
            key in caller.get("with", {}) for key, spec in inputs.items() if spec.get("required")
        )
        assert all(
            key in caller.get("secrets", {})
            for key, spec in secrets.items()
            if spec.get("required")
        )


def test_source_review_caller_passes_only_the_secret() -> None:
    caller = _workflow("agent-review.yml")["jobs"]["agent-review"]

    assert "with" not in caller
    assert caller["secrets"] == {
        "claude_code_oauth_token": "${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}"
    }


def test_caller_permissions_are_a_superset_of_callee_permissions() -> None:
    for caller_file, caller_job, callee_file in (
        ("agent-review.yml", "agent-review", "reusable-agent-review.yml"),
        ("agent-process.yml", "agent-process", "quality.yml"),
    ):
        caller_permissions = _workflow(caller_file)["permissions"]
        callee_permissions = _workflow(callee_file)["permissions"]
        for scope, value in callee_permissions.items():
            assert caller_permissions.get(scope) == value
        assert "id-token" not in caller_permissions
        assert "id-token" not in callee_permissions


TRUSTED_CHECKOUT = {
    "repository": "ekolvah/agent-process-distribution",
    "ref": "${{ job.workflow_sha }}",
    "path": "trusted",
}
NOT_RELEASE = "steps.release.outputs.release != 'true'"


def _run_guard(run: str, sha: str) -> subprocess.CompletedProcess[str]:
    bash = shutil.which("bash")
    assert bash, "bash is unavailable: the guard's run cannot be executed"
    return subprocess.run(
        [bash, "-c", run],
        env={**os.environ, "SHA": sha},
        capture_output=True,
        encoding="utf-8",
        check=False,
    )


def test_trusted_checkout_is_the_called_commit() -> None:
    """Issue 226: the former ref, a `github` context property that does not exist, was empty and made
    `actions/checkout` fall back to the PR's merge ref. The checkout takes the called
    workflow's commit, and an empty one fails the job before the checkout."""
    for name in ("reusable-agent-review.yml", "quality.yml"):
        for job in _workflow(name)["jobs"].values():
            steps = job["steps"]
            for index, step in enumerate(steps):
                if step.get("with", {}).get("path") != "trusted":
                    continue
                assert step["with"]["ref"] == "${{ job.workflow_sha }}", name
                guard = steps[index - 1]
                assert index > 0 and guard.get("name") == "Require the called workflow commit"
                assert guard["env"] == {"SHA": "${{ job.workflow_sha }}"}
                empty = _run_guard(guard["run"], "")
                assert empty.returncode != 0
                assert "job.workflow_sha is empty" in empty.stdout
                assert _run_guard(guard["run"], "a" * 40).returncode == 0


def _assert_detects_a_release_pr(raw: list[dict[str, Any]]) -> None:
    """ADR 0031 D2: the detection runs from the trusted source, after its checkout, on the
    PR's base and head SHAs."""
    names = [step.get("name") for step in raw]
    detect = raw[names.index("Detect a release PR")]
    checkout = next(s for s in raw if s.get("with") == TRUSTED_CHECKOUT)
    assert raw.index(checkout) < raw.index(detect)
    assert detect["id"] == "release"
    assert detect["working-directory"] == "trusted"
    assert "if" not in detect
    run = detect["run"]
    assert "python .agent-process/scripts/release_pr.py" in run
    for argument in (
        "--repo",
        "--pr",
        "--base-sha ${{ github.event.pull_request.base.sha }}",
        "--head-sha ${{ github.event.pull_request.head.sha }}",
    ):
        assert argument in run


def _steps(name: str) -> dict[str, dict[str, Any]]:
    job = next(iter(_workflow(name)["jobs"].values()))
    return {step["name"]: step for step in job["steps"] if "name" in step}


def test_publisher_driver_keeps_a_same_head_catcher() -> None:
    """`agent-process / quality` runs the PR's own driver, so a context the PR cannot change
    stays required beside it: this repository carries the review caller, and activation
    requires its context then (design D5 of v2-2i-protection-activation, D3 of
    v2-4a-review-protection)."""
    from tests.publisher.delivery_fakes import load_script

    assert (ROOT / ".github" / "workflows" / "agent-review.yml").is_file()
    assert "agent-review / agent-review" in load_script("activate_protection").contexts()


def test_quality_runs_once_per_pr() -> None:
    """v2-2j D1: `agent-process / quality` is the only `pull_request` job that runs the
    quality driver."""
    callers = {
        (path.name, name)
        for path in sorted(WORKFLOWS.glob("*.yml"))
        if "pull_request" in (_trigger(_workflow(path.name)) or {})
        for name, job in _workflow(path.name).get("jobs", {}).items()
        if Path(job.get("uses", "").split("@")[0]).name == "quality.yml"
    }

    assert callers == {("agent-process.yml", "agent-process")}


def test_quality_verifies_the_pr_links_its_issue_before_the_driver() -> None:
    """ADR 0027, v2-2c: the PR → issue link is GitHub's `closingIssuesReferences`,
    read once by the first step of the quality callee, before any checkout (`gh`
    reads the API; `GH_REPO` names the repository no worktree provides). An empty
    list is `::error::` naming how to link and how to re-run, then `exit 1`. No
    `shell:` key: `run` is `bash -e {0}`, so a failed read is red, never `ok`."""
    document = _workflow("quality.yml")
    raw = document["jobs"]["link"]["steps"]
    steps = _steps("quality.yml")

    name = "Verify the PR links its issue"
    assert name in steps
    # The only checkout is the trusted process source of the release detection (ADR 0031):
    # nothing of the PR's head runs before the link is read.
    assert all(
        s["with"] == TRUSTED_CHECKOUT
        for s in raw
        if s.get("uses", "").startswith("actions/checkout")
    )
    step = steps[name]
    assert step["env"] == {
        "GH_TOKEN": "${{ github.token }}",
        "GH_REPO": "${{ github.repository }}",
        "PR": "${{ github.event.pull_request.number }}",
    }
    assert "shell" not in step
    run = step["run"]
    assert "--json closingIssuesReferences" in run
    assert ".closingIssuesReferences | length" in run
    assert "::error::" in run
    assert "Closes #N" in run
    assert "gh issue develop -c" in run
    assert "gh run rerun $GITHUB_RUN_ID" in run
    assert "exit 1" in run
    assert run.count("gh pr view") == 1
    assert "sleep" not in run
    assert "verify_pr_link" not in run

    expected = {"contents": "read", "pull-requests": "read", "issues": "read"}
    assert document["permissions"] == expected


def _assert_checkout_and_python(steps: list[dict[str, Any]]) -> None:
    assert steps[0]["uses"] == "actions/checkout@v4"
    assert "with" not in steps[0]
    assert steps[1]["uses"] == "actions/setup-python@v5"
    assert steps[1]["with"]["python-version"] == "3.12"


def test_quality_callee_runs_the_callers_commands() -> None:
    """quality-checks-per-job D1: `link` verifies the PR → issue link; `plan` lists the
    caller's checks (or one unnamed leg without `checks`); `check` runs `setup`, then
    `test --only <name>` per listed check, the name passed through `env`."""
    document = _workflow("quality.yml")
    assert set(_trigger(document)) == {"workflow_call"}
    inputs = _trigger(document)["workflow_call"]["inputs"]
    assert set(inputs) == {"setup", "test", "checks"}
    assert inputs["setup"]["required"] is False
    assert inputs["setup"]["default"] == ""
    assert inputs["test"]["required"] is True
    assert inputs["checks"]["required"] is False
    assert inputs["checks"]["default"] == ""
    assert document["permissions"] == {
        "contents": "read",
        "pull-requests": "read",
        "issues": "read",
    }
    jobs = document["jobs"]
    assert list(jobs) == ["link", "plan", "check", "quality"]

    steps = jobs["link"]["steps"]
    assert [step["name"] for step in steps] == [
        "Require the called workflow commit",
        "Checkout trusted process source",
        "Detect a release PR",
        "Verify the PR links its issue",
    ]

    plan = jobs["plan"]
    _assert_checkout_and_python(plan["steps"])
    listed, single = plan["steps"][2], plan["steps"][3]
    assert len(plan["steps"]) == 4
    assert listed["if"] == "inputs.checks != ''"
    assert "${{ inputs.checks }}" in listed["run"]
    assert "jq -e" in listed["run"]
    assert "length > 0" in listed["run"]
    assert "^[A-Za-z0-9._-]+$" in listed["run"]
    assert '>> "$GITHUB_OUTPUT"' in listed["run"]
    assert single["if"] == "inputs.checks == ''"
    assert "${{ inputs.checks }}" not in single["run"]
    assert 'checks=[""]' in single["run"]
    assert plan["outputs"]["checks"] == (
        f"${{{{ steps.{listed['id']}.outputs.checks || steps.{single['id']}.outputs.checks }}}}"
    )

    check = jobs["check"]
    assert check["needs"] == "plan"
    assert check["strategy"]["matrix"] == {"check": "${{ fromJSON(needs.plan.outputs.checks) }}"}
    assert check["name"] == "${{ matrix.check || 'test' }}"
    _assert_checkout_and_python(check["steps"])
    setup, test = check["steps"][2], check["steps"][3]
    assert len(check["steps"]) == 4
    assert setup["run"] == "${{ inputs.setup }}"
    assert setup["if"] == "inputs.setup != ''"
    assert test["env"] == {"CHECK": "${{ matrix.check }}"}
    assert test["run"] == '${{ inputs.test }} ${CHECK:+--only "$CHECK"}'
    assert "if" not in test

    for job in jobs.values():
        for step in job["steps"]:
            assert "continue-on-error" not in step


def test_quality_gate_requires_every_job() -> None:
    """quality-checks-per-job D3: the gate `quality` runs even when a job it needs failed or
    was skipped, and passes only when every one of them succeeded; no check leg cancels
    another."""
    jobs = _workflow("quality.yml")["jobs"]
    assert jobs["check"]["strategy"]["fail-fast"] is False

    gate = jobs["quality"]
    assert gate["needs"] == ["link", "plan", "check"]
    assert gate["if"] == "always()"
    assert len(gate["steps"]) == 1
    step = gate["steps"][0]
    assert step["env"] == {"NEEDS": "${{ toJSON(needs) }}"}
    assert "jq -e 'all(.[]; .result == \"success\")'" in step["run"]


def test_publisher_caller_reaches_callee_by_same_commit_path() -> None:
    """v2-2h D3: the publisher caller takes the callee from its own commit, so the PR
    that lands `quality.yml` already runs it."""
    document = _workflow("agent-process.yml")
    assert set(_trigger(document)) == {"pull_request"}
    assert _trigger(document)["pull_request"] is None
    assert list(document["jobs"]) == ["agent-process"]
    job = document["jobs"]["agent-process"]
    assert job["uses"] == "./.github/workflows/quality.yml"
    assert job["with"] == {
        "setup": "python -m pip install -r .agent-process/requirements.txt"
        " -r .agent-process/requirements-dev.txt",
        "test": "python .agent-process/scripts/ci_check.py",
        "checks": "python .agent-process/scripts/ci_check.py --list",
    }


def test_the_pr_link_gate_is_gone() -> None:
    """The third caller/callee pair and its driver are deleted (v2-2c): the
    required context `pr-link / pr-link` has no caller to report it."""
    assert not (WORKFLOWS / "pr-link.yml").exists()
    assert not (WORKFLOWS / "reusable-pr-link.yml").exists()
    assert not (ROOT / ".agent-process" / "scripts" / "verify_pr_link.py").exists()


def test_the_copier_answers_are_gone() -> None:
    """remove-copier-leftovers: no script reads the v1 Copier answers file."""
    assert not (ROOT / ".agent-process" / "copier-answers.yml").exists()


def test_the_v1_quality_callee_is_gone() -> None:
    """remove-reusable-quality: the v1 callee has no caller and no consumer, so neither
    the file nor a reference to it survives."""
    assert not (WORKFLOWS / "reusable-quality.yml").exists()
    for path in sorted(WORKFLOWS.iterdir()):
        assert "reusable-quality" not in path.read_text(encoding="utf-8"), path


def test_agent_review_reviews_every_head_and_enforces_threads() -> None:
    """Scenario: New head — the job reads once whether its closing comment names the head,
    runs the Claude action only when it does not, verifies the action published, and fails
    on an unresolved P0/P1 thread. Nothing parses a review and nobody requests one. Every
    event runs the same path: a skipped job would pass the required check (#137)."""
    document = _workflow("reusable-agent-review.yml")
    job = document["jobs"]["agent-review"]
    steps = _steps("reusable-agent-review.yml")

    assert list(steps) == [
        "Checkout reviewed PR head",
        "Require the called workflow commit",
        "Checkout trusted review source",
        "Detect a release PR",
        "Read the Claude review of the head",
        "Claude review",
        "Verify the Claude review of the head",
        "Enforce unresolved P0/P1 threads",
    ]
    assert len(job["steps"]) == len(steps)
    assert "inputs" not in (_trigger(document)["workflow_call"] or {})
    text = (WORKFLOWS / "reusable-agent-review.yml").read_text(encoding="utf-8")
    assert "codex" not in text.lower()

    assert steps["Checkout reviewed PR head"]["with"] == {
        "fetch-depth": 0,
        "ref": "${{ github.event.pull_request.head.sha }}",
    }
    assert steps["Checkout trusted review source"]["with"] == TRUSTED_CHECKOUT

    # Scenarios: Re-run on a reviewed head, Reader failure — one read, no wait: `gh run
    # rerun` re-executes every step, so a head the job reviewed returns on its closing
    # comment (issue 139). Absence (exit 3) is the step's recorded output; a crash of the
    # reader (exit 2) fails the step and the job, so the action never runs on a read that
    # did not establish absence.
    read = steps["Read the Claude review of the head"]
    assert read["id"] == "review"
    assert "continue-on-error" not in read
    assert read["working-directory"] == "trusted"
    assert read["if"] == NOT_RELEASE
    assert "head_review.py --wait" in read["run"]
    assert "--timeout-seconds 0" in read["run"]
    assert '0) echo "absent=false" >> "$GITHUB_OUTPUT"' in read["run"]
    assert '3) echo "absent=true" >> "$GITHUB_OUTPUT"' in read["run"]
    assert '*) exit "$rc"' in read["run"]

    # Scenarios: Event other than a push, Head from a fork — absence is the only
    # condition: no event filter and no fork guard; the platform withholds every secret
    # but GITHUB_TOKEN from a fork run and requires approval for an external contributor
    # (ADR 0027).
    absent = "steps.review.outputs.absent == 'true'"
    claude = steps["Claude review"]
    assert claude["if"] == absent
    assert claude["uses"].startswith("anthropics/claude-code-action@")
    assert claude["with"]["claude_code_oauth_token"] == "${{ secrets.claude_code_oauth_token }}"
    assert claude["with"]["github_token"] == "${{ github.token }}"
    assert "mcp__github_inline_comment__create_inline_comment" in claude["with"]["claude_args"]
    assert "--json-schema" not in claude["with"]["claude_args"]
    prompt = claude["with"]["prompt"]
    # The closing comment is the review: the action publishes finding by finding, so an
    # interrupted action has left inline comments and no closing comment, and the
    # second attempt reviews again (issue 139).
    for anchor in (
        "trusted/.agent-process/REVIEW_CONTRACT.md",
        "untrusted",
        "P0",
        "last, on every review",
        "Reviewed head SHA: <sha>",
        "Never approve",
    ):
        assert anchor in prompt

    # Scenario: Silent action — the action can finish green without publishing
    # (ADR 0004); a bounded read of its closing comment fails the check instead.
    verify = steps["Verify the Claude review of the head"]
    assert verify["if"] == absent
    assert "continue-on-error" not in verify
    assert verify["working-directory"] == "trusted"
    assert "head_review.py --wait" in verify["run"]
    assert "--timeout-seconds 60" in verify["run"]
    assert "|| rc" not in verify["run"]

    enforce = steps["Enforce unresolved P0/P1 threads"]
    assert enforce["if"] == "always()"
    assert enforce["working-directory"] == "trusted"
    assert "check_blocking_review_threads.py" in enforce["run"]

    for step in job["steps"]:
        assert "check_agent_review_outcome" not in str(step)
        assert "STANDARD_REVIEW_PARSER" not in str(step)
    assert (
        "reusable-agent-review.yml@"
        in _workflow("agent-review.yml")["jobs"]["agent-review"]["uses"]
    )


_HEAD = "a" * 40
_EXPRESSIONS = {
    "github.repository": "owner/repo",
    "github.event.pull_request.number": "1",
    "github.event.pull_request.head.sha": _HEAD,
}


def test_review_steps_call_head_review_with_its_arguments(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Scenario: New head — the argv of both workflow calls is the reader's own CLI: a
    drift on either side fails here instead of failing every head's review."""
    steps = _steps("reusable-agent-review.yml")
    closing = {
        "author": {"login": "github-actions[bot]"},
        "body": f"No findings. Reviewed head SHA: {_HEAD}",
    }
    pull = {"headRefOid": _HEAD, "reviews": {"nodes": []}, "comments": {"nodes": [closing]}}
    payload = {"data": {"repository": {"pullRequest": pull}}}
    monkeypatch.setattr(head_review, "run_gh", lambda args: json.dumps(payload))
    monkeypatch.setattr(head_review.time, "sleep", lambda seconds: None)
    script = ".agent-process/scripts/head_review.py"

    for name in ("Read the Claude review of the head", "Verify the Claude review of the head"):
        run = re.sub(
            r"\$\{\{\s*(.*?)\s*\}\}", lambda m: _EXPRESSIONS[m.group(1)], steps[name]["run"]
        )
        assert script in run, name
        call = run[run.index(script) :].split("||")[0].replace("\\\n", " ")
        argv = shlex.split(call)
        assert argv[0] == script

        head_review.main(argv[1:])

        assert "present" in capsys.readouterr().out, name


def test_agent_review_caller_runs_on_pushes_alone() -> None:
    """Scenario: Review event re-runs the check — by the fixer's `gh run rerun` of
    the head's `pull_request` run, not by an event: every event is a required
    context of its own, so a `pull_request_review` run leaves the `pull_request`
    context as it was (PR #137: `BLOCKED` with the review-event runs green, `CLEAN`
    after the rerun). GitHub rejects `pull_request_review_thread`."""
    trigger = _trigger(_workflow("agent-review.yml"))

    assert set(trigger) == {"pull_request"}
    assert trigger["pull_request"]["types"] == ["opened", "synchronize"]


def test_review_contract_is_a_file_not_an_agents_section_parser() -> None:
    contract = ROOT / ".agent-process" / "REVIEW_CONTRACT.md"

    assert contract.is_file()
    assert "[REVIEW_CONTRACT.md](.agent-process/REVIEW_CONTRACT.md)" in (
        ROOT / "AGENTS.md"
    ).read_text(encoding="utf-8")
    assert not (ROOT / ".agent-process" / "scripts" / "extract_review_prompt.py").exists()


def test_review_contract_and_principles_stay_coupled_on_narrow_simplicity_triggers() -> None:
    contract = (ROOT / ".agent-process" / "REVIEW_CONTRACT.md").read_text(encoding="utf-8")
    principles = (ROOT / "skills" / "agent-process" / "principles.md").read_text(encoding="utf-8")

    indirection_marker = "single call site and no stated reason"
    duplication_marker = "names an existing symbol and its repository-relative path"

    def bullet_containing(text: str, anchor: str) -> str:
        assert anchor in text, f"REVIEW_CONTRACT.md is missing the {anchor!r} clause"
        anchor_index = text.index(anchor)
        bullet_start = text.rindex("\n- ", 0, anchor_index) + 1
        next_bullet = text.find("\n- ", anchor_index)
        return text[bullet_start : next_bullet if next_bullet != -1 else len(text)]

    # One reviewer clause for both apps (v2-2b): the contract is the prompt each reads.
    clause = bullet_containing(contract, "Assign **P0 or P1**")

    for marker in (indirection_marker, duplication_marker):
        assert marker in clause, f"priority-assignment clause is missing the {marker!r} trigger"
        assert marker in principles, f"principles.md §VII is missing the {marker!r} trigger"
    assert "BLOCKING" not in contract
    assert "deferred-scope" not in contract


def test_no_workflow_step_resolves_a_review_thread() -> None:
    """ADR 0022/0027: only the fixer's local session resolves a thread, and no
    workflow step classifies one or reads a review outcome (v2-2b)."""
    for path in sorted(WORKFLOWS.glob("*.yml")):
        document = _workflow(path.name)
        for job in document.get("jobs", {}).values():
            for step in job.get("steps") or ():
                for forbidden in (
                    "resolve_review_thread",
                    "--classify",
                    "/replies",
                    "check_agent_review_outcome",
                ):
                    assert forbidden not in (step.get("run") or "")
                    assert forbidden not in (step.get("uses") or "")


def test_pr_title_requires_a_conventional_commit_type() -> None:
    """ADR 0030: the `pr-title` job is the context the `pr-title` ruleset requires."""
    document = _workflow("pr-title.yml")
    assert _trigger(document) == {
        "pull_request": {"types": ["opened", "edited", "synchronize", "reopened"]}
    }
    assert list(document["jobs"]) == ["pr-title"]
    job = document["jobs"]["pr-title"]
    assert job["permissions"] == {"pull-requests": "read"}
    (step,) = job["steps"]
    assert step["uses"] == "amannn/action-semantic-pull-request@v6"
    assert step["with"]["types"].split() == ["feat", "fix", "docs", "test", "refactor", "chore"]


def test_quality_skips_the_link_on_a_release_pr() -> None:
    """ADR 0031: a release PR is exempt from the issue link alone; the tests still run."""
    jobs = _workflow("quality.yml")["jobs"]
    raw = jobs["link"]["steps"]

    _assert_detects_a_release_pr(raw)
    link = next(s for s in raw if s.get("name") == "Verify the PR links its issue")
    assert link["if"] == NOT_RELEASE
    assert "if" not in jobs["plan"]
    assert "if" not in jobs["check"]
    assert jobs["quality"]["needs"] == ["link", "plan", "check"]


def test_agent_review_skips_the_review_on_a_release_pr() -> None:
    """ADR 0031: a release PR reads no review and gets none; the P0/P1 enforcement still
    runs on its head."""
    raw = _workflow("reusable-agent-review.yml")["jobs"]["agent-review"]["steps"]
    steps = _steps("reusable-agent-review.yml")

    _assert_detects_a_release_pr(raw)
    assert steps["Read the Claude review of the head"]["if"] == NOT_RELEASE
    assert steps["Claude review"]["if"] == "steps.review.outputs.absent == 'true'"
    assert steps["Verify the Claude review of the head"]["if"] == (
        "steps.review.outputs.absent == 'true'"
    )
    assert steps["Enforce unresolved P0/P1 threads"]["if"] == "always()"


def test_release_workflow_enables_auto_merge() -> None:
    """ADR 0031 D4: the release workflow enables auto-merge on the PR it created or
    updated, with the PAT that opened it; the required checks decide the merge."""
    (job,) = _workflow("release-please.yml")["jobs"].values()
    raw = job["steps"]
    action = next(s for s in raw if s.get("uses", "").startswith("googleapis/release-please"))
    assert action["id"] == "release"

    merge = raw[raw.index(action) + 1]
    assert merge["if"] == "steps.release.outputs.prs_created == 'true'"
    assert merge["env"]["GH_TOKEN"] == "${{ secrets.RELEASE_PLEASE_TOKEN }}"
    assert merge["env"]["PR_JSON"] == "${{ steps.release.outputs.pr }}"
    assert "PR" not in merge["env"]
    assert "jq -er .number" in merge["run"]
    assert 'gh pr merge --auto --squash "$PR"' in merge["run"]


def test_release_workflow_parses_no_unset_output() -> None:
    """#213: the runner evaluates a step's `env` although its `if` is false, and an output
    the guarded step needs may be unset then; `fromJSON('')` fails the run."""
    (job,) = _workflow("release-please.yml")["jobs"].values()
    guarded = [s for s in job["steps"] if "steps." in str(s.get("if", ""))]
    assert guarded
    for step in guarded:
        for value in step.get("env", {}).values():
            assert "fromJSON" not in str(value), step.get("name")


def test_release_workflow_moves_stable() -> None:
    """Scenarios: Release created, No release — a release fast-forwards `stable` to its
    tagged commit with the tagging token; a refused update fails the run (#199)."""
    (job,) = _workflow("release-please.yml")["jobs"].values()
    raw = job["steps"]
    merge = next(s for s in raw if s.get("name") == "Enable auto-merge on the release PR")
    assert raw.index(merge) + 1 < len(raw), "no step after the auto-merge step"
    move = raw[raw.index(merge) + 1]
    assert move["if"] == "steps.release.outputs.release_created == 'true'"
    assert move["env"]["GH_TOKEN"] == "${{ secrets.RELEASE_PLEASE_TOKEN }}"
    assert move["env"]["SHA"] == "${{ steps.release.outputs.sha }}"
    run = move["run"]
    assert "-X PATCH" in run and "git/refs/heads/stable" in run
    assert '-f sha="$SHA"' in run and "-F force=false" in run
    assert "--force" not in run and "force=true" not in run
    assert "continue-on-error" not in move
    assert "|| true" not in run and "set +e" not in run
