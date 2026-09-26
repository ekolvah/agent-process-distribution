"""The v2 target spec validates under OpenSpec's strict rules (issue #105).

OpenSpec is the spec format and validator; this test only runs it, so a delta
with a scenario-less requirement, a missing SHALL, or a malformed heading fails
CI instead of waiting for a reviewer. Node is a v2 dependency of the process
(``openspec`` runs through ``npx``), so a machine without it fails visibly
rather than skipping.
"""

from __future__ import annotations

from tests.publisher.openspec_cli import _openspec


def test_openspec_changes_and_specs_validate_strictly() -> None:
    completed = _openspec("validate", "--strict", "--all")
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "0 failed" in completed.stdout, completed.stdout
