"""The pinned OpenSpec CLI, run through `npx`, shared by the OpenSpec test modules."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from tests.publisher.init_harness import load_init

ROOT = Path(__file__).resolve().parents[2]
OPENSPEC = f"@fission-ai/openspec@{load_init().OPENSPEC}"


def _openspec(*args: str, cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    npx = shutil.which("npx")
    assert npx, "npx not found: Node is required to validate openspec/ (see CLAUDE.md)"
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
