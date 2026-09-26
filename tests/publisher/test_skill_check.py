"""The Claude session-start skill check (change skill-presence-check, #187).

The check runs as the hook runs it: a subprocess of `templates/skill_check.py` with the Install
URL as its argument. The `claude` CLI is the process boundary: a fake first on PATH prints the
listing a test gives it and exits with the test's code.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
CHECK = ROOT / "skills" / "agent-process" / "templates" / "skill_check.py"
PLUGIN = "agent-process@agent-process-marketplace"
URL = "https://example.invalid/blob/v9.9.9/skills/agent-process/SKILL.md#install"
MARKER = "agent-process skill not loaded"


def _fake_claude(bin_dir: Path, stdout: str, code: int) -> None:
    bin_dir.mkdir()
    (bin_dir / "out.txt").write_text(stdout, encoding="utf-8")
    fake = bin_dir / "fake.py"
    fake.write_text(
        "import sys, pathlib\n"
        "sys.stdout.write(pathlib.Path(__file__).with_name('out.txt').read_text('utf-8'))\n"
        f"sys.exit({code})\n",
        encoding="utf-8",
    )
    if os.name == "nt":
        (bin_dir / "claude.cmd").write_text(f'@"{sys.executable}" "{fake}" %*\n', encoding="utf-8")
    else:
        script = bin_dir / "claude"
        script.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{fake}" "$@"\n', encoding="utf-8")
        script.chmod(0o755)


def _install(tmp_path: Path, name: str, skill: bool = True) -> str:
    path = tmp_path / "cache" / name
    (path / "skills" / "agent-process").mkdir(parents=True)
    if skill:
        (path / "skills" / "agent-process" / "SKILL.md").write_text("skill\n", encoding="utf-8")
    return str(path)


def _entry(install_path: str, scope: str = "user", **fields: Any) -> dict[str, Any]:
    return {
        "id": PLUGIN,
        "version": Path(install_path).name,
        "scope": scope,
        "enabled": True,
        "installPath": install_path,
        **fields,
    }


def _run(
    tmp_path: Path, stdout: str | None, code: int = 0, args: tuple[str, ...] = (URL,)
) -> subprocess.CompletedProcess[str]:
    project = tmp_path / "project"
    project.mkdir(exist_ok=True)
    bin_dir = tmp_path / "bin"
    if stdout is None:
        bin_dir.mkdir()
    else:
        _fake_claude(bin_dir, stdout, code)
    env = {**os.environ, "PATH": str(bin_dir), "CLAUDE_PROJECT_DIR": str(project)}
    return subprocess.run(
        [sys.executable, str(CHECK), *args],
        cwd=project,
        env=env,
        capture_output=True,
        encoding="utf-8",
        timeout=60,
    )


def _marked(done: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    assert done.returncode == 0, done.stderr
    out = json.loads(done.stdout)
    context = out["hookSpecificOutput"]
    assert context["hookEventName"] == "SessionStart"
    for text in (out["systemMessage"], context["additionalContext"]):
        assert MARKER in text
    return out


def test_loaded_is_silent(tmp_path: Path) -> None:
    listing = [_entry(_install(tmp_path, "2.0.0"))]
    done = _run(tmp_path, json.dumps(listing))
    assert (done.returncode, done.stdout) == (0, ""), done.stderr


def test_case_differing_project_paths_are_one_project(tmp_path: Path) -> None:
    project = str(tmp_path / "project")
    install = _install(tmp_path, "2.0.0")
    listing = [
        _entry(install, scope="project", projectPath=project),
        _entry(install, scope="project", projectPath=project.swapcase()),
    ]
    done = _run(tmp_path, json.dumps(listing))
    assert (done.returncode, done.stdout) == (0, ""), done.stderr


def _not_loaded(tmp_path: Path, case: str) -> list[dict[str, Any]]:
    good = _install(tmp_path, "2.0.0")
    if case == "no-entry":
        return [{**_entry(good), "id": "other@elsewhere"}]
    if case == "disabled":
        return [_entry(good, enabled=False)]
    if case == "other-project":
        return [_entry(good, scope="project", projectPath=str(tmp_path / "elsewhere"))]
    if case == "several-installs":
        old = _install(tmp_path, "0.1.0")
        return [
            _entry(good),
            _entry(old, scope="project", projectPath=str(tmp_path / "project")),
        ]
    assert case == "no-skill"
    return [_entry(_install(tmp_path, "0.1.0", skill=False))]


@pytest.mark.parametrize(
    "case", ["no-entry", "disabled", "other-project", "several-installs", "no-skill"]
)
def test_not_loaded_is_marked(tmp_path: Path, case: str) -> None:
    out = _marked(_run(tmp_path, json.dumps(_not_loaded(tmp_path, case))))
    for text in (out["systemMessage"], out["hookSpecificOutput"]["additionalContext"]):
        assert URL in text


@pytest.mark.parametrize(
    ("case", "stdout", "code", "args"),
    [
        ("no-cli", None, 0, (URL,)),
        ("cli-fails", "[]", 1, (URL,)),
        ("not-json", "Plugins:\n  none\n", 0, (URL,)),
        ("not-a-list", '{"plugins": []}', 0, (URL,)),
        ("no-url", "[]", 0, ()),
    ],
)
def test_undecidable_is_marked(
    tmp_path: Path, case: str, stdout: str | None, code: int, args: tuple[str, ...]
) -> None:
    out = _marked(_run(tmp_path, stdout, code, args))
    assert "cannot check" in out["systemMessage"], case
