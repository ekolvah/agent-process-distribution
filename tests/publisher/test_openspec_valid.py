"""The v2 target spec validates under OpenSpec's strict rules (issue #105).

OpenSpec is the spec format and validator; this test only runs it, so a delta
with a scenario-less requirement, a missing SHALL, or a malformed heading fails
CI instead of waiting for a reviewer. Node is a v2 dependency of the process
(``openspec`` runs through ``npx``), so a machine without it fails visibly
rather than skipping.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OPENSPEC = "@fission-ai/openspec@1.13.0"


def _openspec(*args: str) -> subprocess.CompletedProcess[str]:
    npx = shutil.which("npx")
    assert npx, "npx not found: Node is required to validate openspec/ (see AGENTS.md)"
    return subprocess.run(
        [npx, "-y", OPENSPEC, *args],
        cwd=ROOT,
        env={**os.environ, "OPENSPEC_TELEMETRY": "0"},
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=180,
    )


def test_openspec_changes_and_specs_validate_strictly() -> None:
    completed = _openspec("validate", "--strict", "--all")
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "0 failed" in completed.stdout, completed.stdout


def test_forked_schema_validates() -> None:
    """The forked `agent-process` schema (v2-1) stays valid against the OpenSpec it was forked from."""
    completed = _openspec("schema", "validate", "agent-process")
    assert completed.returncode == 0, completed.stdout + completed.stderr
