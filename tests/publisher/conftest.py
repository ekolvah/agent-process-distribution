"""Fixtures of the installer tests; their harness is `init_harness.py`."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

from tests.publisher.init_harness import (
    CURRENT,
    OTHER,
    PACKAGE,
    STUB,
    Sandbox,
    consumer_repo,
    git,
    hook_mirror,
    hook_repositories,
)

# The interpreter is quoted: pre-commit splits the entry, and its path may hold a space.
_PROBE = "import os, pathlib; pathlib.Path(os.environ['HOME'], 'pre-push-ran').touch()"
_ENTRY = f'"{Path(sys.executable).as_posix()}" -c "{_PROBE}"'
PROBE_HOOK = f"""\
- id: quality
  name: quality
  entry: {json.dumps(_ENTRY)}
  language: system
  stages: [pre-push]
  always_run: true
  pass_filenames: false
"""


@pytest.fixture(scope="module")
def process_repo(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A bare repository: `v{CURRENT}` carries this tree's skill and a `quality` hook that
    records its run in `$HOME/pre-push-ran` (change hermetic-sandbox-push, design D3),
    `v{OTHER}` the recording stub."""
    base = tmp_path_factory.mktemp("process")
    work = base / "work"
    shutil.copytree(
        PACKAGE, work / "skills" / "agent-process", ignore=shutil.ignore_patterns("__pycache__")
    )
    (work / ".pre-commit-hooks.yaml").write_text(PROBE_HOOK, encoding="utf-8")
    git("init", "-q", str(work))
    git("add", "-A", cwd=work)
    git("commit", "-q", "-m", f"v{CURRENT}", cwd=work)
    git("tag", f"v{CURRENT}", cwd=work)
    (work / "skills" / "agent-process" / "scripts" / "init.py").write_text(STUB, encoding="utf-8")
    git("commit", "-q", "-am", f"v{OTHER}", cwd=work)
    git("tag", f"v{OTHER}", cwd=work)
    bare = base / "process.git"
    git("clone", "-q", "--bare", str(work), str(bare))
    for url, (rev, ids) in hook_repositories().items():
        mirror = hook_mirror(bare, url)
        _hook_mirror(base / "mirrors" / mirror.stem, mirror, rev, ids)
    return bare


def _hook_mirror(work: Path, bare: Path, rev: str, ids: list[str]) -> None:
    """A bare repository tagged `rev` whose manifest declares `ids`: what pre-commit needs to
    load a repository whose hooks the run does not select."""
    manifest = [{"id": i, "name": i, "entry": i, "language": "unsupported"} for i in ids]
    work.mkdir(parents=True)
    (work / ".pre-commit-hooks.yaml").write_text(json.dumps(manifest), encoding="utf-8")
    git("init", "-q", str(work))
    git("add", "-A", cwd=work)
    git("commit", "-q", "-m", rev, cwd=work)
    git("tag", rev, cwd=work)
    git("clone", "-q", "--bare", str(work), str(bare))


@pytest.fixture
def sandbox(tmp_path: Path, process_repo: Path, monkeypatch: pytest.MonkeyPatch) -> Sandbox:
    root, home, other = tmp_path / "consumer", tmp_path / "home", tmp_path / "other"
    for path in (root, home, other):
        path.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.setenv("AGENT_PROCESS_REPOSITORY", str(process_repo))
    monkeypatch.delenv("STUB_EXIT", raising=False)
    sb = Sandbox(root, home, process_repo, other)
    consumer_repo(sb)
    return sb
