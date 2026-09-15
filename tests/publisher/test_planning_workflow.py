"""Planning runs on the OpenSpec skills with project rules (change v2-1b-planning-schema).

One test per scenario of the change's spec deltas that a script can prove; the
scenario name is the test name.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from tests.publisher.test_openspec_valid import OPENSPEC

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = ROOT / "openspec" / "schemas" / "agent-process" / "schema.yaml"
CONFIG = ROOT / "openspec" / "config.yaml"
REVIEWER = ROOT / "agents" / "architect-reviewer.md"
ARCHIVE = ROOT / ".agent-process" / "scripts" / "archive_change.py"
_V1_ENTRY_POINTS = (
    "commands/plan.md",
    "commands/implement.md",
    "agents/discovery.md",
    ".agents/skills/plan-issue",
    ".agents/skills/implement-issue",
    ".agents/orchestration/change-classes.yaml",
    ".agent-process/scripts/validate_issue_sections.py",
    ".agent-process/scripts/capture_external_fixture.py",
    ".agent-process/scripts/check_fixture_ratchet.py",
    "tests/agent_process/test_validate_issue_status.py",
)


def test_roles_and_carriers() -> None:
    """Scenario: Procedure changes once — one schema, one config; both agents read them."""
    schema = yaml.safe_load(SCHEMA.read_text(encoding="utf-8"))
    assert [a["id"] for a in schema["artifacts"]] == [
        "proposal",
        "specs",
        "design",
        "tasks",
        "architect-review",
    ]
    assert set(schema["apply"]["requires"]) == {"tasks", "architect-review"}
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    assert config["schema"] == "agent-process"
    rules = config["rules"]
    assert {"proposal", "tasks", "architect-review"} <= set(rules)
    assert set(rules) <= {a["id"] for a in schema["artifacts"]}


def test_review_finding() -> None:
    """Scenario: Review finding — the review reads the task list; its map gaps are findings."""
    schema = yaml.safe_load(SCHEMA.read_text(encoding="utf-8"))
    review = next(a for a in schema["artifacts"] if a["id"] == "architect-review")
    assert "tasks" in review["requires"]
    rules = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))["rules"]
    assert "no RED" in " ".join(rules["tasks"])
    # A `rework` verdict is not an approved plan: the apply instruction and the first
    # delivery task both stop on it (artifact status is file existence only).
    assert "rework" in schema["apply"]["instruction"]
    assert "rework" in " ".join(rules["tasks"])


def test_tasks_of_a_new_change() -> None:
    """Scenario: Tasks of a new change — priority before the issue, the archive before the PR."""
    rule = " ".join(yaml.safe_load(CONFIG.read_text(encoding="utf-8"))["rules"]["tasks"])
    assert rule.index("priority") < rule.index("gh issue create")
    assert rule.index("archive_change.py") < rule.index("gh pr create")
    assert "finish_change" not in rule
    # No tick after the archive (a pushed tick would move the reviewed head); a run
    # interrupted after it resumes from the PR, not from the apply.
    assert "no tick" in rule
    assert rule.index("archive_change.py") < rule.index("gh pr view --head <change>")


def test_pinned_openspec() -> None:
    """The commands the process runs use the version the tests validate against."""
    for path in (CONFIG, REVIEWER, ARCHIVE):
        text = path.read_text(encoding="utf-8")
        assert "openspec@latest" not in text, path
        assert OPENSPEC in text, path


def test_one_planning_home() -> None:
    """A change lives in the repository whose PR archives it: no registered store anywhere."""
    context = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))["context"]
    assert "registered store" in context
    for path in (CONFIG, REVIEWER):
        assert "--store" not in path.read_text(encoding="utf-8"), path


def test_label_change() -> None:
    """Scenario: Label change — no per-label artifact sets, no discovery role, no v1 planner."""
    present = [p for p in _V1_ENTRY_POINTS if (ROOT / p).exists()]
    assert present == []
