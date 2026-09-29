"""The bash that tests execute shell code with."""

from __future__ import annotations

import shutil


def git_bash() -> str:
    """Absolute path to `bash`."""
    bash = shutil.which("bash")
    assert bash, "bash недоступен: хук нечем исполнить, гард выродился бы в grep"
    return bash
