"""Running the plugin's hook commands as Claude Code does, for the plugin tests."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PLUGIN_HOOKS = ROOT / "hooks" / "hooks.json"


def plugin_hooks() -> dict[str, Any]:
    """The plugin's `hooks/hooks.json`."""
    return json.loads(PLUGIN_HOOKS.read_text(encoding="utf-8"))


def run_plugin_hook(
    project: Path, command: str, payload: dict, extra: dict[str, str | None] | None = None
) -> subprocess.CompletedProcess:
    """Run a hook command as the platform does: `sh -c`, the plugin root and project exported;
    `extra` sets variables, or removes the ones it maps to None."""
    sh = shutil.which("sh")
    assert sh, "sh is not on PATH"
    merged: dict[str, str | None] = {
        **os.environ,
        "CLAUDE_PROJECT_DIR": project.as_posix(),
        "CLAUDE_PLUGIN_ROOT": ROOT.as_posix(),
        **(extra or {}),
    }
    env = {name: value for name, value in merged.items() if value is not None}
    return subprocess.run(
        [sh, "-c", command],
        cwd=project,
        env=env,
        input=json.dumps(payload),
        capture_output=True,
        encoding="utf-8",
        check=False,
    )
