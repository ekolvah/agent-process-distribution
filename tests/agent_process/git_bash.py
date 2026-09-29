"""The bash that tests execute shell code with (#88).

On Windows the first `bash` on a registry PATH is `System32\\bash.exe`, the WSL launcher; Git
runs hooks with its own `usr/bin/bash.exe` instead, so tests take that one, derived from
`git --exec-path` (`<root>/mingw64/libexec/git-core`), and never search PATH there.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


def git_bash() -> str:
    """Absolute path to the bash Git runs hooks with; a missing one fails the test."""
    if os.name == "nt":
        exec_path = subprocess.run(
            ["git", "--exec-path"], capture_output=True, encoding="utf-8", check=True
        ).stdout.strip()
        bash = Path(exec_path).parents[2] / "usr" / "bin" / "bash.exe"
        assert bash.is_file(), f"Git's bash not found at {bash} (from `git --exec-path`)"
        return str(bash)
    bash = shutil.which("bash")
    assert bash, "bash недоступен: хук нечем исполнить, гард выродился бы в grep"
    return bash
