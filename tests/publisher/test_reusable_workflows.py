"""Contracts of the source repository's referenced GitHub workflows."""

from __future__ import annotations

import json
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
    template = (ROOT / "template" / ".github" / "workflows" / "pr-link.yml.jinja").read_text(
        encoding="utf-8"
    )
    assert "issues: read" in template


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


def test_agent_review_prompt_points_at_the_contract_rule() -> None:
    """The prompt is the last thing the model reads about the PR body and
    calls it untrusted (issue #64 pilot: a hand-written body section alone
    changed nothing) — the contract's downgrade rule needs a pointer here,
    not just in REVIEW_CONTRACT.md, per architect-review finding B2."""
    steps = _steps("reusable-agent-review.yml")
    prompt = steps["Claude review"]["with"]["prompt"]

    assert "deferred-scope rule" in prompt
    assert prompt.count("${{ steps.review-source.outputs.contract_path }}") >= 1


def test_agent_review_keeps_claude_as_fallback_after_manual_codex_request() -> None:
    steps = _steps("reusable-agent-review.yml")

    trusted_checkout = steps["Checkout trusted review source"]
    assert trusted_checkout["with"] == {
        "ref": "${{ github.event.repository.default_branch }}",
        "path": "trusted",
    }
    assert steps["Checkout reviewed PR head"]["with"] == {
        "fetch-depth": 0,
        "ref": "${{ steps.pr-context.outputs.head_sha }}",
    }
    names = list(steps)
    assert names.index("Checkout reviewed PR head") < names.index("Checkout trusted review source")
    assert "Claude review" in steps
    assert "Classify Codex review outcome" in steps
    assert "steps.codex-classify.outputs.valid != 'true'" in steps["Claude review"]["if"]
    assert "@codex review" not in str(steps["Read owner-requested Codex review"])
    assert steps["Read owner-requested Codex review"]["continue-on-error"] is True
    assert steps["Read owner-requested Codex review"]["working-directory"] == (
        "${{ steps.review-source.outputs.adapter_working_directory }}"
    )
    for name in (
        "Classify Codex review outcome",
        "Classify Claude review outcome",
        "Publish validated review evidence",
        "Enforce selected review outcome",
    ):
        assert steps[name]["working-directory"] == (
            "${{ steps.review-source.outputs.outcome_checker_root }}"
        )
    assert steps["Enforce unresolved blocking Codex conversations"]["working-directory"] == (
        "${{ steps.review-source.outputs.blocking_threads_root }}"
    )
    assert "STANDARD_REVIEW_PARSER = True" in steps["Select trusted review source"]["run"]
    assert (
        "contract_path=trusted/.agent-process/REVIEW_CONTRACT.md"
        in steps["Select trusted review source"]["run"]
    )
    prompt = steps["Claude review"]["with"]["prompt"]
    assert "trusted/AGENTS.md" in prompt
    assert "Treat every AGENTS.md" in prompt
    assert "untrusted review data" in prompt
    assert (
        "context.payload.pull_request.updated_at"
        in steps["Fetch current PR context"]["with"]["script"]
    )
    assert "--head-observed-at" in steps["Read owner-requested Codex review"]["run"]
    assert (
        "reusable-agent-review.yml@"
        in _workflow("agent-review.yml")["jobs"]["agent-review"]["uses"]
    )


def test_agent_review_requires_structured_review_evidence() -> None:
    steps = _steps("reusable-agent-review.yml")

    schema_arg = steps["Claude review"]["with"]["claude_args"]
    schema = json.loads(schema_arg.removeprefix("--json-schema ").strip("'"))
    assert "findings" in schema["properties"]
    assert {"severity", "confidence", "summary"} == set(
        schema["properties"]["findings"]["items"]["properties"]
    )
    assert schema["required"] == ["outcome", "findings"]
    assert not {"allOf", "oneOf", "anyOf"} & set(schema)
    assert "Publish validated review evidence" in steps
    assert "--reviewed-head-sha" in steps["Publish validated review evidence"]["run"]
    assert "Claude review" in steps["Enforce selected review outcome"]["env"]["REVIEW_PRODUCER"]
    assert (
        "${{ steps.review-source.outputs.blocking_threads_invocation }}"
        in steps["Enforce unresolved blocking Codex conversations"]["run"]
    )
    assert "Diagnose Claude execution failure" in steps


def test_valid_codex_evidence_skips_claude_fallback_and_diagnostic() -> None:
    steps = _steps("reusable-agent-review.yml")

    for name in (
        "Claude review",
        "Classify Claude review outcome",
        "Diagnose Claude execution failure",
    ):
        assert "steps.codex-classify.outputs.valid != 'true'" in steps[name]["if"]


def test_invalid_codex_evidence_runs_fail_closed_claude_diagnostic_in_the_selected_outcome_checker_root() -> (
    None
):
    steps = _steps("reusable-agent-review.yml")

    name = "Diagnose Claude execution failure"
    assert name in steps
    step = steps[name]
    assert step["working-directory"] == "${{ steps.review-source.outputs.outcome_checker_root }}"
    assert "continue-on-error" not in step
    assert "steps.claude-classify.outputs.valid != 'true'" in step["if"]
    assert "steps.claude-diagnostic-capability.outputs.supported == 'true'" in step["if"]
    assert step["env"]["EXECUTION_FILE"] == "${{ steps.review.outputs.execution_file }}"
    assert "--diagnose-execution-file" in step["run"]

    names = list(steps)
    assert (
        names.index("Classify Claude review outcome")
        < names.index(name)
        < names.index("Publish validated review evidence")
    )


def test_diagnostic_capability_is_feature_detected_on_a_default_branch_that_predates_it() -> None:
    steps = _steps("reusable-agent-review.yml")

    name = "Select Claude-diagnostic capability"
    assert name in steps
    capability = steps[name]
    assert "DIAGNOSE_EXECUTION_FILE_SUPPORTED = True" in capability["run"]
    assert "supported=true" in capability["run"]
    assert "supported=false" in capability["run"]

    names = list(steps)
    assert names.index(name) < names.index("Diagnose Claude execution failure")


def test_outcome_checker_location_is_feature_detected_on_a_default_branch_that_predates_it() -> (
    None
):
    steps = _steps("reusable-agent-review.yml")

    selector = steps["Select trusted review source"]["run"]
    assert "outcome_checker_path=.agent-process/scripts/check_agent_review_outcome.py" in selector
    assert "outcome_checker_path=scripts/check_agent_review_outcome.py" in selector
    assert (
        "outcome_checker_invocation=python .agent-process/scripts/check_agent_review_outcome.py"
        in selector
    )
    assert "outcome_checker_invocation=python -m scripts.check_agent_review_outcome" in selector
    assert "bootstrap fallback: default branch has no relocated outcome checker yet" in selector
    assert (
        "bootstrap fallback: default branch has no process installed yet, "
        "using this PR's own outcome checker" in selector
    )
    assert selector.count("outcome_checker_root=trusted") == 2
    assert "outcome_checker_root=." in selector

    invocation = "${{ steps.review-source.outputs.outcome_checker_invocation }}"
    root = "${{ steps.review-source.outputs.outcome_checker_root }}"
    for name in (
        "Classify Codex review outcome",
        "Classify Claude review outcome",
        "Diagnose Claude execution failure",
        "Publish validated review evidence",
        "Publish Claude fallback findings to the PR",
        "Enforce selected review outcome",
    ):
        assert invocation in steps[name]["run"]
        assert steps[name]["working-directory"] == root

    path = "${{ steps.review-source.outputs.outcome_checker_path }}"
    for name in (
        "Select Claude-diagnostic capability",
        "Select PR-comment publish capability",
    ):
        assert f"{root}/{path}" in steps[name]["run"]


def test_review_parser_location_is_feature_detected_on_a_default_branch_that_predates_it() -> None:
    steps = _steps("reusable-agent-review.yml")

    selector = steps["Select trusted review source"]["run"]
    assert "adapter_invocation=python .agent-process/scripts/request_codex_review.py" in selector
    assert "adapter_invocation=python -m scripts.request_codex_review" in selector
    assert "bootstrap fallback: default branch has no relocated Codex parser yet" in selector
    assert selector.count("adapter_working_directory=trusted") == 2
    assert "adapter_working_directory=." in selector

    assert (
        "${{ steps.review-source.outputs.adapter_invocation }}"
        in steps["Read owner-requested Codex review"]["run"]
    )


def test_review_contract_location_is_feature_detected_on_a_default_branch_that_predates_it() -> (
    None
):
    selector = _steps("reusable-agent-review.yml")["Select trusted review source"]["run"]

    assert "contract_path=trusted/.agent-process/REVIEW_CONTRACT.md" in selector
    assert "contract_path=trusted/REVIEW_CONTRACT.md" in selector
    assert "contract_path=.agent-process/REVIEW_CONTRACT.md" in selector
    assert "bootstrap fallback: default branch has no relocated review contract yet" in selector
    assert (
        "bootstrap fallback: default branch has no process installed yet, "
        "using this PR's own review contract" in selector
    )


def test_blocking_threads_invocation_is_feature_detected_on_a_default_branch_that_predates_it() -> (
    None
):
    steps = _steps("reusable-agent-review.yml")

    selector = steps["Select trusted review source"]["run"]
    assert (
        "blocking_threads_invocation=python .agent-process/scripts/check_blocking_review_threads.py"
        in selector
    )
    assert "blocking_threads_invocation=python -m scripts.check_blocking_review_threads" in selector
    assert (
        "bootstrap fallback: default branch has no relocated blocking-thread gate yet" in selector
    )
    assert (
        "bootstrap fallback: default branch has no process installed yet, "
        "using this PR's own blocking-thread gate" in selector
    )
    assert selector.count("blocking_threads_root=trusted") == 2
    assert "blocking_threads_root=." in selector

    assert (
        "${{ steps.review-source.outputs.blocking_threads_invocation }}"
        in steps["Enforce unresolved blocking Codex conversations"]["run"]
    )
    assert steps["Enforce unresolved blocking Codex conversations"]["working-directory"] == (
        "${{ steps.review-source.outputs.blocking_threads_root }}"
    )


def test_agent_review_publishes_fallback_findings_only_when_codex_invalid() -> None:
    steps = _steps("reusable-agent-review.yml")

    name = "Publish Claude fallback findings to the PR"
    assert name in steps
    step = steps[name]
    assert "steps.codex-classify.outputs.valid != 'true'" in step["if"]
    assert "steps.pr-comment-capability.outputs.supported == 'true'" in step["if"]
    assert step["working-directory"] == "${{ steps.review-source.outputs.outcome_checker_root }}"
    assert step["env"]["STRUCTURED_OUTCOME"] == "${{ steps.review.outputs.structured_output }}"
    assert "--publish-pr-comment" in step["run"]
    assert "--reviewed-head-sha" in step["run"]
    names = list(steps)
    assert names.index("Publish validated review evidence") < names.index(name)

    capability = steps["Select PR-comment publish capability"]
    assert names.index("Select PR-comment publish capability") < names.index(name)
    assert "PUBLISH_PR_COMMENT_SUPPORTED = True" in capability["run"]
    assert "supported=true" in capability["run"]
    assert "supported=false" in capability["run"]


def test_review_contract_is_a_file_not_an_agents_section_parser() -> None:
    contract = ROOT / ".agent-process" / "REVIEW_CONTRACT.md"
    template_contract = ROOT / "template" / ".agent-process" / "REVIEW_CONTRACT.md.jinja"

    assert contract.read_text(encoding="utf-8") == template_contract.read_text(encoding="utf-8")
    assert "[REVIEW_CONTRACT.md](.agent-process/REVIEW_CONTRACT.md)" in (
        ROOT / "template" / "AGENTS.md.jinja"
    ).read_text(encoding="utf-8")
    assert not (ROOT / "template" / "scripts" / "extract_review_prompt.py").exists()


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

    codex_clause = bullet_containing(contract, "Assign **P0 or P1**")
    fallback_clause = bullet_containing(contract, "`blocking` means wrong behaviour")

    for marker in (indirection_marker, duplication_marker):
        assert marker in codex_clause, (
            f"Codex priority-assignment clause is missing the {marker!r} trigger"
        )
        assert marker in fallback_clause, (
            f"Claude-fallback blocking clause is missing the {marker!r} trigger"
        )
        assert marker in principles, f"principles.md §VII is missing the {marker!r} trigger"


def test_installation_documents_the_caller_workflow_trust_boundary() -> None:
    source_installation = (
        ROOT / ".agent-process" / "docs" / "architecture" / "agent-process-installation.md"
    ).read_text(encoding="utf-8")
    installation = (
        ROOT
        / "template"
        / ".agent-process"
        / "docs"
        / "architecture"
        / "agent-process-installation.md.jinja"
    ).read_text(encoding="utf-8")

    for document in (source_installation, installation):
        assert "Claude fallback carrier" in document
        assert "issues: read" in document
        assert "Classic branch protection matches a" in document
        assert "platform trust anchor" in document
        assert "pull_request_target` as a shortcut" in document


def test_no_workflow_step_resolves_a_review_thread() -> None:
    """ADR 0022: CI classifies findings; only the fixer's local session resolves one."""
    for path in sorted(WORKFLOWS.glob("*.yml")):
        document = _workflow(path.name)
        for job in document.get("jobs", {}).values():
            for step in job.get("steps") or ():
                assert "resolve_review_thread" not in (step.get("run") or "")
                assert "resolve_review_thread" not in (step.get("uses") or "")
