"""Published workflow references must point at the trusted branch, not a stale pin."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
_MAIN_REF = re.compile(r"^[^@]+@main$")


def test_copier_workflow_references_point_at_main() -> None:
    config = yaml.safe_load((ROOT / "copier.yml").read_text(encoding="utf-8"))
    references = config["workflow_references"]["default"]

    assert all(_MAIN_REF.fullmatch(reference) for reference in references.values())
