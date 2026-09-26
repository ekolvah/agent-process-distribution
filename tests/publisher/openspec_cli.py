"""The pinned OpenSpec CLI, run through `npx`, shared by the OpenSpec test modules."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OPENSPEC = "@fission-ai/openspec@1.13.0"


def _openspec(*args: str, cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    npx = shutil.which("npx")
    assert npx, "npx not found: Node is required to validate openspec/ (see AGENTS.md)"
    return subprocess.run(
        [npx, "-y", OPENSPEC, *args],
        cwd=cwd,
        env={**os.environ, "OPENSPEC_TELEMETRY": "0"},
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=180,
    )
