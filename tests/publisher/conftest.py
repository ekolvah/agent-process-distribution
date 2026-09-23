"""Fixtures of the installer tests; their harness is `init_harness.py`."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from tests.publisher.init_harness import (
    PACKAGE,
    STUB,
    Sandbox,
    git,
)


@pytest.fixture(scope="module")
def process_repo(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A bare repository: `v2.0.0` carries this tree's skill, `v2.1.0` the recording stub."""
    base = tmp_path_factory.mktemp("process")
    work = base / "work"
    shutil.copytree(
        PACKAGE, work / "skills" / "agent-process", ignore=shutil.ignore_patterns("__pycache__")
    )
    git("init", "-q", str(work))
    git("add", "-A", cwd=work)
    git("commit", "-q", "-m", "v2.0.0", cwd=work)
    git("tag", "v2.0.0", cwd=work)
    (work / "skills" / "agent-process" / "scripts" / "init.py").write_text(STUB, encoding="utf-8")
    git("commit", "-q", "-am", "v2.1.0", cwd=work)
    git("tag", "v2.1.0", cwd=work)
    bare = base / "process.git"
    git("clone", "-q", "--bare", str(work), str(bare))
    return bare


@pytest.fixture
def sandbox(tmp_path: Path, process_repo: Path, monkeypatch: pytest.MonkeyPatch) -> Sandbox:
    root, home, other = tmp_path / "consumer", tmp_path / "home", tmp_path / "other"
    for path in (root, home, other):
        path.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.setenv("AGENT_PROCESS_REPOSITORY", str(process_repo))
    monkeypatch.delenv("STUB_EXIT", raising=False)
    return Sandbox(root, home, process_repo, other)
