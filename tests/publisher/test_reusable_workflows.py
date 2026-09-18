"""Contracts of the source repository's referenced GitHub workflows."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"


def _workflow(name: str) -> dict[Any, Any]:
    return yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8"))


def _trigger(document: dict[Any, Any]) -> Any:
    return document.get("on", document.get(True))


def test_callees_declare_workflow_call_without_pull_request_trigger() -> None:
    for name in (
        "reusable-quality.yml",
        "reusable-pr-link.yml",
        "reusable-agent-review.yml",
    ):
        trigger = _trigger(_workflow(name))
        assert "workflow_call" in trigger
        assert "pull_request" not in trigger


def test_callee_schema_matches_local_callers_in_both_directions() -> None:
    pairs = (
        ("ci.yml", "quality", "reusable-quality.yml", "quality"),
        ("pr-link.yml", "pr-link", "reusable-pr-link.yml", "pr-link"),
        (
            "agent-review.yml",
            "agent-review",
            "reusable-agent-review.yml",
            "agent-review",
        ),
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


def test_source_review_caller_passes_only_the_claude_fallback_secret() -> None:
    caller = _workflow("agent-review.yml")["jobs"]["agent-review"]

    assert caller["secrets"] == {
        "claude_code_oauth_token": "${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}"
    }


def test_caller_permissions_are_a_superset_of_callee_permissions() -> None:
    for caller_file, caller_job, callee_file in (
        ("ci.yml", "quality", "reusable-quality.yml"),
        ("pr-link.yml", "pr-link", "reusable-pr-link.yml"),
        ("agent-review.yml", "agent-review", "reusable-agent-review.yml"),
    ):
        caller_permissions = _workflow(caller_file)["permissions"]
        callee_permissions = _workflow(callee_file)["permissions"]
        for scope, value in callee_permissions.items():
            assert caller_permissions.get(scope) == value
        assert "id-token" not in caller_permissions
        assert "id-token" not in callee_permissions


def _steps(name: str) -> dict[str, dict[str, Any]]:
    job = next(iter(_workflow(name)["jobs"].values()))
    return {step["name"]: step for step in job["steps"] if "name" in step}


def test_quality_executes_a_trusted_driver_against_the_pr_worktree() -> None:
    steps = _steps("reusable-quality.yml")

    trusted_checkout = steps["Checkout trusted quality driver"]
    assert trusted_checkout["with"] == {
        "ref": "${{ github.event.repository.default_branch }}",
        "path": "trusted",
    }
    assert steps["Checkout PR under test"]["with"] == {"path": "pr"}
    assert _trigger(_workflow("reusable-quality.yml"))["workflow_call"] is None
    assert "reusable-quality.yml@" in _workflow("ci.yml")["jobs"]["quality"]["uses"]
    assert steps["Install consumer dependencies"]["working-directory"] == "pr"
    assert steps["Run trusted quality checks"]["working-directory"] == "pr"
    assert steps["Run trusted quality checks"]["run"] == (
        'python "$GITHUB_WORKSPACE/${{ steps.quality-driver.outputs.path }}/.agent-process/scripts/ci_check.py"'
    )
    assert "trusted/.agent-process/scripts/ci_check.py" in steps["Select quality driver"]["run"]
    assert 'echo "path=pr"' in steps["Select quality driver"]["run"]


def test_quality_installs_product_dependencies_when_present() -> None:
    """A consumer's own product dependencies must be installed before its
    checks run — the trusted-driver step only ever installed the process's
    own two lockfiles, so a consumer whose product tests import a dependency
    outside those locks failed for reasons unrelated to its code (#57)."""
    steps = _steps("reusable-quality.yml")

    name = "Install product dependencies"
    assert name in steps
    step = steps[name]
    assert step["working-directory"] == "pr"
    assert "requirements.txt" in step["run"]
    # A consumer that declares dependencies only in a package `pyproject.toml`
    # (no root requirements.txt) needs its own installation path — the earlier
    # fix only ever recognized requirements.txt (#57 fresh finding).
    assert "pyproject.toml" in step["run"]
    assert "pip install -e ." in step["run"]
    # Only a packaging-capable pyproject.toml (a literal `[project]` table)
    # counts: this repository's own root pyproject.toml holds tool config
    # only, with no installable package, and running `pip install -e .`
    # against it fails setuptools' flat-layout auto-discovery (regression
    # caught live on #57's own self-applied quality gate). setup.cfg/setup.py/
    # Poetry-style pyproject.toml support is deferred to a dedicated issue.
    assert "grep" in step["run"]
    assert r"^\[project\]" in step["run"]
    names = list(steps)
    assert (
        names.index("Install consumer dependencies")
        < names.index(name)
        < names.index("Run trusted quality checks")
    )


def test_pr_link_uses_a_bootstrap_fallback_only_when_main_has_no_driver() -> None:
    steps = _steps("reusable-pr-link.yml")

    assert steps["Checkout trusted PR-link driver"]["with"] == {
        "ref": "${{ github.event.repository.default_branch }}",
        "path": "trusted",
    }
    assert steps["Checkout PR under test"]["with"] == {"path": "pr"}
    assert steps["Verify PR closes its issue"]["working-directory"] == (
        "${{ steps.pr-link-driver.outputs.path }}"
    )
    driver_run = steps["Select PR-link driver"]["run"]
    assert "trusted/.agent-process/scripts/verify_pr_link.py" in driver_run
    # The default branch may still carry only the pre-migration root path
    # (relocation not yet merged there); that must resolve to the trusted
    # driver too, via its module invocation, not fall through to the PR's
    # own untrusted copy (#57 fresh finding).
    assert "trusted/scripts/verify_pr_link.py" in driver_run
    assert "python -m scripts.verify_pr_link" in driver_run
    assert steps["Verify PR closes its issue"]["run"] == (
        '${{ steps.pr-link-driver.outputs.invocation }} --branch "$HEAD_REF" --pr "$PR_NUMBER"'
    )
    checkouts = [step for step in steps.values() if step.get("uses") == "actions/checkout@v4"]
    assert len(checkouts) == 2
    assert "reusable-pr-link.yml@" in _workflow("pr-link.yml")["jobs"]["pr-link"]["uses"]


def test_pr_link_grants_issues_read() -> None:
    """The deferred-scope soundness check reads the linked issue's body
    (issue #64 finding B5): without `issues: read` the gate's `gh issue view`
    call is a silent 403, not a missing capability the operator ever sees."""
    assert _workflow("reusable-pr-link.yml")["permissions"]["issues"] == "read"
    assert _workflow("pr-link.yml")["permissions"]["issues"] == "read"


def test_pr_link_feature_detects_deferred_scope_support() -> None:
    steps = _steps("reusable-pr-link.yml")

    name = "Select deferred-scope check capability"
    assert name in steps
    capability = steps[name]
    assert "DEFERRED_SCOPE_CHECK_SUPPORTED = True" in capability["run"]
    assert "supported=true" in capability["run"]
    assert "supported=false" in capability["run"]

    names = list(steps)
    assert names.index(name) < names.index("Verify PR closes its issue")


def test_pr_link_installs_its_driver_dependencies() -> None:
    """Codex finding on PR #66: verify_pr_link.py now imports
    check_orphan_scope.py, which hard-imports the third-party markdown_it
    package at module level, but this driver never installed anything before
    invoking it — every issue-branch PR would red with ModuleNotFoundError
    once this reaches the default branch."""
    steps = _steps("reusable-pr-link.yml")

    name = "Install PR-link driver dependencies"
    assert name in steps
    step = steps[name]
    assert "requirements.txt" in step["run"]

    names = list(steps)
    assert names.index(name) < names.index("Verify PR closes its issue")


def test_agent_review_waits_for_codex_falls_back_to_claude_and_enforces_threads() -> None:
    """ADR 0027, v2-2b: the job reads whether a Codex review of the head exists,
    runs the Claude action only when it does not, and fails on an unresolved
    P0/P1 thread. Nothing parses a review. Every event runs the same path: a
    review-event run that skipped the wait and the fallback would pass on a head
    without any review and become the required context (#137, round 3)."""
    document = _workflow("reusable-agent-review.yml")
    job = document["jobs"]["agent-review"]
    steps = _steps("reusable-agent-review.yml")

    assert list(steps) == [
        "Checkout reviewed PR head",
        "Checkout trusted review source",
        "Wait for the Codex review of the head",
        "Claude review",
        "Verify the Claude review of the head",
        "Enforce unresolved P0/P1 threads",
    ]
    assert len(job["steps"]) == len(steps)
    assert "codex-timeout-seconds" in _trigger(document)["workflow_call"]["inputs"]

    assert steps["Checkout reviewed PR head"]["with"] == {
        "fetch-depth": 0,
        "ref": "${{ github.event.pull_request.head.sha }}",
    }
    assert steps["Checkout trusted review source"]["with"] == {
        "repository": "ekolvah/agent-process-distribution",
        "ref": "${{ github.job_workflow_sha }}",
        "path": "trusted",
    }

    # Absence (exit 3) is the step's recorded output, not its failure; a crash of the
    # reader (exit 2) fails the step and with it the job — the fallback never runs on
    # a read that did not establish absence.
    wait = steps["Wait for the Codex review of the head"]
    assert wait["id"] == "codex"
    assert "continue-on-error" not in wait
    assert wait["working-directory"] == "trusted"
    assert "if" not in wait
    assert "request_codex_review.py --wait" in wait["run"]
    assert "inputs.codex-timeout-seconds" in wait["run"]
    assert '3) echo "absent=true" >> "$GITHUB_OUTPUT"' in wait["run"]
    assert '*) exit "$rc"' in wait["run"]

    # Absence is the only condition: no event filter (a skipped job passes a required
    # check) and no fork guard — the platform withholds every secret but GITHUB_TOKEN
    # from a run of a fork PR on `pull_request` and `pull_request_review` alike, and the
    # repository requires approval for every run from an external contributor (ADR 0027).
    claude = steps["Claude review"]
    assert claude["if"] == "steps.codex.outputs.absent == 'true'"
    assert claude["uses"].startswith("anthropics/claude-code-action@")
    assert claude["with"]["claude_code_oauth_token"] == "${{ secrets.claude_code_oauth_token }}"
    assert claude["with"]["github_token"] == "${{ github.token }}"
    assert "mcp__github_inline_comment__create_inline_comment" in claude["with"]["claude_args"]
    assert "--json-schema" not in claude["with"]["claude_args"]
    prompt = claude["with"]["prompt"]
    for anchor in (
        "trusted/.agent-process/REVIEW_CONTRACT.md",
        "untrusted",
        "P0",
        "Reviewed head SHA",
        "Never approve",
    ):
        assert anchor in prompt

    # A fallback that completes without publishing is no review of the head (ADR 0004
    # records the action finishing green without a comment): the same presence read as
    # for Codex, on the job's own login, fails the check instead of leaving it green.
    verify = steps["Verify the Claude review of the head"]
    assert verify["if"] == "steps.codex.outputs.absent == 'true'"
    assert "continue-on-error" not in verify
    assert verify["working-directory"] == "trusted"
    assert "request_codex_review.py --wait" in verify["run"]
    assert "--reviewer github-actions" in verify["run"]

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
    principles = (ROOT / ".agent-process" / "docs" / "architecture" / "principles.md").read_text(
        encoding="utf-8"
    )

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


def test_installation_documents_the_caller_workflow_trust_boundary() -> None:
    document = (
        ROOT / ".agent-process" / "docs" / "architecture" / "agent-process-installation.md"
    ).read_text(encoding="utf-8")

    assert "Claude fallback carrier" in document
    assert "P0/P1" in document
    assert "@codex review" in document
    assert "issues: read" in document
    assert "Classic branch protection matches a" in document
    assert "platform trust anchor" in document
    assert "pull_request_target` as a shortcut" in document


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
