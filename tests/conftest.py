"""Shared Copier render fixtures for source-repository integration tests."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def rendered_default(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Render default answers once instead of repeating identical Copier work."""
    destination = tmp_path_factory.mktemp("copier-render") / "rendered"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "copier",
            "copy",
            str(ROOT),
            str(destination),
            "--vcs-ref",
            "HEAD",
            "--defaults",
            "--trust",
        ],
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    return destination
