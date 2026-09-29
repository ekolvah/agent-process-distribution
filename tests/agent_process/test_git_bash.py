"""`git_bash()`: tests run shell code with Git's bash, not the first `bash` on PATH (#88)."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from tests.agent_process.git_bash import git_bash

_SYSTEM32 = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32"


@pytest.mark.skipif(
    os.name != "nt" or not (_SYSTEM32 / "bash.exe").is_file(),
    reason="the WSL launcher System32\\bash.exe exists only on Windows with WSL",
)
def test_launcher_first_on_path_is_not_selected(monkeypatch: pytest.MonkeyPatch) -> None:
    """A registry PATH puts System32 before Git; its `bash.exe` is the WSL launcher."""
    monkeypatch.setenv("PATH", str(_SYSTEM32) + os.pathsep + os.environ["PATH"])
    result = subprocess.run(
        [git_bash(), "-c", 'echo "$OSTYPE"'],
        capture_output=True,
        encoding="utf-8",
        check=False,
    )
    assert result.returncode == 0, result
    assert result.stdout.strip() in ("msys", "cygwin"), result
