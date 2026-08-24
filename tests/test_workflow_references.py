"""Published workflow pins must contain the contracts their callers promise."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
_PIN = re.compile(r"^[^@]+@[0-9a-f]{40}$")
_OWNER_REQUESTED_CARRIER_REVISION = (
    "d3f6d238891dbaee6af10b18609e7e07f8901921"  # pragma: allowlist secret
)


def test_copier_workflow_references_share_a_published_revision() -> None:
    config = yaml.safe_load((ROOT / "copier.yml").read_text(encoding="utf-8"))
    references = config["workflow_references"]["default"]

    assert all(_PIN.fullmatch(reference) for reference in references.values())
    revisions = {reference.rsplit("@", 1)[1] for reference in references.values()}
    assert len(revisions) == 1

    assert revisions == {_OWNER_REQUESTED_CARRIER_REVISION}
