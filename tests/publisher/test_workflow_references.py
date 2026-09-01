"""Published workflow pins must contain the contracts their callers promise."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
_PIN = re.compile(r"^[^@]+@[0-9a-f]{40}$")
_PUBLISHED_REVISIONS = {
    "quality": "2bdd924dca3626db3daca7cfbab843c50c0e26c9",  # pragma: allowlist secret
    "pr-link": "2bdd924dca3626db3daca7cfbab843c50c0e26c9",  # pragma: allowlist secret
    "agent-review": "2bdd924dca3626db3daca7cfbab843c50c0e26c9",  # pragma: allowlist secret
}


def test_copier_workflow_references_pin_the_published_contracts() -> None:
    config = yaml.safe_load((ROOT / "copier.yml").read_text(encoding="utf-8"))
    references = config["workflow_references"]["default"]

    assert all(_PIN.fullmatch(reference) for reference in references.values())
    assert {
        name: reference.rsplit("@", 1)[1] for name, reference in references.items()
    } == _PUBLISHED_REVISIONS
