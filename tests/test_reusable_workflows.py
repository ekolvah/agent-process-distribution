"""Contracts of the source repository's referenced GitHub workflows."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
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


def test_source_review_caller_has_no_provider_secret() -> None:
    caller = _workflow("agent-review.yml")["jobs"]["agent-review"]

    assert "secrets" not in caller


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
    assert _workflow("ci.yml")["jobs"]["quality"]["uses"] == (
        "./.github/workflows/reusable-quality.yml"
    )
    assert steps["Install consumer dependencies"]["working-directory"] == "pr"
    assert steps["Run trusted quality checks"]["working-directory"] == "pr"
    assert steps["Run trusted quality checks"]["run"] == (
        'python "$GITHUB_WORKSPACE/${{ steps.quality-driver.outputs.path }}/scripts/ci_check.py"'
    )
    assert "trusted/scripts/ci_check.py" in steps["Select quality driver"]["run"]
    assert 'echo "path=pr"' in steps["Select quality driver"]["run"]


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
    assert "trusted/scripts/verify_pr_link.py" in steps["Select PR-link driver"]["run"]
    checkouts = [step for step in steps.values() if step.get("uses") == "actions/checkout@v4"]
    assert len(checkouts) == 2
    assert _workflow("pr-link.yml")["jobs"]["pr-link"]["uses"] == (
        "./.github/workflows/reusable-pr-link.yml"
    )


def test_agent_review_reads_manual_codex_evidence_from_trusted_source() -> None:
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
    assert "Claude review" not in steps
    assert "Classify Codex review outcome" not in steps
    assert "@codex review" not in str(steps["Read owner-requested Codex review"])
    for name in (
        "Read owner-requested Codex review",
        "Publish validated Codex review evidence",
        "Enforce Codex review outcome",
    ):
        assert steps[name]["working-directory"] == (
            "${{ steps.review-source.outputs.working_directory }}"
        )
    assert "STANDARD_REVIEW_PARSER = True" in steps["Select trusted review source"]["run"]
    assert _workflow("agent-review.yml")["jobs"]["agent-review"]["uses"] == (
        "./.github/workflows/reusable-agent-review.yml"
    )


def test_agent_review_requires_structured_review_evidence() -> None:
    steps = _steps("reusable-agent-review.yml")

    assert "Publish validated Codex review evidence" in steps
    assert "--reviewed-head-sha" in steps["Publish validated Codex review evidence"]["run"]
    assert steps["Enforce Codex review outcome"]["env"]["REVIEW_PRODUCER"] == "Codex review"


def test_review_contract_is_a_file_not_an_agents_section_parser() -> None:
    contract = ROOT / "REVIEW_CONTRACT.md"
    template_contract = ROOT / "template" / "REVIEW_CONTRACT.md.jinja"

    assert contract.read_text(encoding="utf-8") == template_contract.read_text(encoding="utf-8")
    assert "[REVIEW_CONTRACT.md](REVIEW_CONTRACT.md)" in (
        ROOT / "template" / "AGENTS.md.jinja"
    ).read_text(encoding="utf-8")
    assert not (ROOT / "template" / "scripts" / "extract_review_prompt.py").exists()


def test_installation_documents_the_caller_workflow_trust_boundary() -> None:
    installation = (
        ROOT / "template" / "docs" / "architecture" / "agent-process-installation.md.jinja"
    ).read_text(encoding="utf-8")

    assert "Classic branch protection matches a" in installation
    assert "platform trust anchor" in installation
    assert "pull_request_target` as a shortcut" in installation
