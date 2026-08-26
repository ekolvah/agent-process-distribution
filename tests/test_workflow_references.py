"""Published workflow pins must contain the contracts their callers promise."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
_PIN = re.compile(r"^[^@]+@[0-9a-f]{40}$")
_PUBLISHED_REVISIONS = {
    "quality": "d3f6d238891dbaee6af10b18609e7e07f8901921",  # pragma: allowlist secret
    "pr-link": "d3f6d238891dbaee6af10b18609e7e07f8901921",  # pragma: allowlist secret
    "agent-review": "69db0363304b43a256deb02a0e2cbb11797118de",  # pragma: allowlist secret
}


def test_copier_workflow_references_pin_the_published_contracts() -> None:
    config = yaml.safe_load((ROOT / "copier.yml").read_text(encoding="utf-8"))
    references = config["workflow_references"]["default"]

    assert all(_PIN.fullmatch(reference) for reference in references.values())
    assert {
        name: reference.rsplit("@", 1)[1] for name, reference in references.items()
    } == _PUBLISHED_REVISIONS
