"""Published workflow pins must contain the contracts their callers promise."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
_PIN = re.compile(r"^[^@]+@[0-9a-f]{40}$")


def test_copier_workflow_references_share_a_published_revision() -> None:
    config = yaml.safe_load((ROOT / "copier.yml").read_text(encoding="utf-8"))
    references = config["workflow_references"]["default"]

    assert all(_PIN.fullmatch(reference) for reference in references.values())
    revisions = {reference.rsplit("@", 1)[1] for reference in references.values()}
    assert len(revisions) == 1

    revision = revisions.pop()
    result = subprocess.run(
        ["git", "show", f"{revision}:.github/workflows/reusable-agent-review.yml"],
        cwd=ROOT,
        capture_output=True,
        check=True,
        encoding="utf-8",
        text=True,
    )

    assert "Read owner-requested Codex review" in result.stdout
    assert "Claude review" in result.stdout
    assert "--head-observed-at" in result.stdout
