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
    assert "no RED" in " ".join(
        yaml.safe_load(CONFIG.read_text(encoding="utf-8"))["rules"]["tasks"]
    )


def test_pinned_openspec() -> None:
    """The commands the process runs use the version the tests validate against."""
    for path in (CONFIG, REVIEWER):
        text = path.read_text(encoding="utf-8")
        assert "openspec@latest" not in text, path
        assert OPENSPEC in text, path
