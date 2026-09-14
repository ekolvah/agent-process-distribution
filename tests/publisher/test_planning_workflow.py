"""Planning runs on the OpenSpec skills with project rules (change v2-1b-planning-schema).

One test per scenario of the change's spec deltas that a script can prove; the
scenario name is the test name.
"""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = ROOT / "openspec" / "schemas" / "agent-process" / "schema.yaml"
CONFIG = ROOT / "openspec" / "config.yaml"


def test_roles_and_carriers() -> None:
    """Scenario: Procedure changes once — one schema, one config; both agents read them."""
    schema = yaml.safe_load(SCHEMA.read_text(encoding="utf-8"))
    assert [a["id"] for a in schema["artifacts"]] == [
        "proposal",
        "specs",
        "design",
        "architect-review",
        "tasks",
    ]
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    assert config["schema"] == "agent-process"
    rules = config["rules"]
    assert {"proposal", "tasks", "architect-review"} <= set(rules)
    assert set(rules) <= {a["id"] for a in schema["artifacts"]}
