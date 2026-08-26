"""Source-root activation guard for GitHub Project bootstrap (issue #7).

A rendered consumer starts with an unconfigured ``scripts/project_settings.py``;
this source repository is the one checkout that must always carry the real
GitHub Project it delivers its own issues through. This is a committed-state
guard, not proof that the persisted IDs point at the correct Project: it fails
only if the settings module goes missing or reverts to the unconfigured shape
that ships in ``template/scripts/project_settings.py``.
"""

from __future__ import annotations

import importlib


def test_committed_project_settings_are_configured() -> None:
    from scripts import project_settings

    project_settings = importlib.reload(project_settings)
    project_settings.require_configured()
