"""Contracts of the v2 one-caller GitHub workflow."""

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


def _steps(name: str, job: str = "quality") -> dict[str, dict[str, Any]]:
    return {step["name"]: step for step in _workflow(name)["jobs"][job]["steps"] if "name" in step}


def test_quality_check_on_a_pr() -> None:
    document = _workflow("reusable-quality.yml")
    call = _trigger(document)["workflow_call"]
    assert call["inputs"] == {
        "setup": {
            "description": "Optional consumer setup command.",
            "required": False,
            "type": "string",
            "default": "",
        },
        "test": {"description": "Consumer quality command.", "required": True, "type": "string"},
    }
    steps = _steps("reusable-quality.yml")
    assert steps["Checkout PR head"]["with"]["ref"] == "${{ github.event.pull_request.head.sha }}"
    assert steps["Run consumer setup"]["if"] == "inputs.setup != ''"
    assert steps["Run consumer setup"]["run"] == "${{ inputs.setup }}"
    assert steps["Run consumer quality"]["run"] == "${{ inputs.test }}"


def test_consumer_test_failure_is_quality_failure() -> None:
    step = _steps("reusable-quality.yml")["Run consumer quality"]
    assert "continue-on-error" not in step
    assert "if" not in step


def test_quality_verifies_issue_link_and_strict_openspec() -> None:
    steps = _steps("reusable-quality.yml")
    names = list(steps)
    assert names[0] == "Verify the PR links its issue"
    assert "--json closingIssuesReferences" in steps[names[0]]["run"]
    assert "gh run rerun $GITHUB_RUN_ID" in steps[names[0]]["run"]
    validate = steps["Validate OpenSpec"]
    assert "@fission-ai/openspec@1.13.0" in validate["run"]
    assert "validate --strict --all" in validate["run"]
    assert "openspec" in validate["if"]


def test_one_caller_and_publisher_inputs() -> None:
    assert {p.name for p in WORKFLOWS.glob("*.yml")} == {
        "agent-process.yml",
        "reusable-quality.yml",
    }
    caller = _workflow("agent-process.yml")
    assert set(caller["jobs"]) == {"quality", "review"}
    quality = caller["jobs"]["quality"]
    assert "pip install" in quality["with"]["setup"]
    assert "ci_check.py" in quality["with"]["test"]


def test_consumer_caller_pins_release_tag() -> None:
    template = (ROOT / "skills" / "agent-process" / "templates" / "agent-process.yml").read_text(
        encoding="utf-8"
    )
    assert (
        "ekolvah/agent-process-distribution/.github/workflows/reusable-quality.yml@v2.0.0"
    ) in template


def test_publisher_caller_uses_local_reusable() -> None:
    quality = _workflow("agent-process.yml")["jobs"]["quality"]
    assert quality["uses"] == "./.github/workflows/reusable-quality.yml"


def test_direct_advisory_reviews() -> None:
    review = _workflow("agent-process.yml")["jobs"]["review"]
    steps = {step["name"]: step for step in review["steps"]}
    claude = steps["Claude review"]
    assert claude["uses"] == "anthropics/claude-code-action@v1"
    assert claude["with"]["claude_code_oauth_token"] == "${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}"
    joined = json.dumps(review)
    for forbidden in (
        "request_codex_review",
        "check_blocking_review_threads",
        "review_gate",
        "fallback",
    ):
        assert forbidden not in joined


def test_review_is_visible_but_not_required() -> None:
    review = _workflow("agent-process.yml")["jobs"]["review"]
    assert "continue-on-error" not in review
    ruleset = json.loads(
        (ROOT / "skills" / "agent-process" / "templates" / "ruleset.json").read_text(
            encoding="utf-8"
        )
    )
    required = next(r for r in ruleset["rules"] if r["type"] == "required_status_checks")
    assert [c["context"] for c in required["parameters"]["required_status_checks"]] == [
        "quality / quality"
    ]


def test_dependabot_tracks_github_actions() -> None:
    config = yaml.safe_load((ROOT / ".github" / "dependabot.yml").read_text(encoding="utf-8"))
    entry = next(
        item for item in config["updates"] if item["package-ecosystem"] == "github-actions"
    )
    assert entry["directory"] == "/"
    assert entry["schedule"]["interval"] == "weekly"


def test_no_workflow_step_resolves_or_parses_a_review() -> None:
    for path in WORKFLOWS.glob("*.yml"):
        text = path.read_text(encoding="utf-8")
        for forbidden in ("resolve_review_thread", "check_agent_review_outcome", "@codex review"):
            assert forbidden not in text
