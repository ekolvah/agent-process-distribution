"""The memory checkpoint: a reminder after a write into the agent's auto-memory directory.

Driven through the CLI only, as the plugin hook runs it: `post-edit` with the PostToolUse
payload on stdin. A write under `.claude/projects/<project>/memory/` exits 2 (Claude Code
shows the stderr to the agent; the write already happened); anything else is silent.
"""

from __future__ import annotations

import json
import subprocess
import sys

import pytest

from tests.publisher.delivery_fakes import SKILL_SCRIPTS

_SCRIPT = SKILL_SCRIPTS / "memory_checkpoint.py"


def _run(args: list[str], stdin: str = "") -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, _SCRIPT, *args],
        input=stdin,
        capture_output=True,
        encoding="utf-8",
        check=False,
    )


def _write(path: str) -> str:
    return json.dumps({"tool_name": "Write", "tool_input": {"file_path": path}})


@pytest.mark.parametrize(
    "path",
    [
        "/home/u/.claude/projects/slug/memory/fact.md",
        r"C:\Users\u\.claude\projects\slug\memory\fact.md",
        "/home/u/.claude/projects/slug/memory/MEMORY.md",
        # Non-ASCII home directory: the Windows code page must not mangle or crash it.
        r"C:\Users\Иван\.claude\projects\slug\memory\fact.md",
    ],
)
def test_memory_write_is_flagged(path: str) -> None:
    """Scenario: Memory write — exit 2, stderr names the file and asks the D4 question."""
    result = _run(["post-edit"], _write(path))
    assert result.returncode == 2, result.stderr
    assert path in result.stderr
    assert "every session" in result.stderr
    assert "repository" in result.stderr
    assert "machine" not in result.stderr


@pytest.mark.parametrize(
    "stdin",
    [
        _write("src/x.py"),
        _write(".claude/rules/mindset.md"),
        _write("~/.claude/projects/slug/other/f.md"),
        json.dumps({"tool_name": "Write"}),
        "",
        "{not json",
    ],
)
def test_writes_outside_memory_are_silent(stdin: str) -> None:
    """Scenario: Write outside auto-memory — exit 0, no output."""
    result = _run(["post-edit"], stdin)
    assert (result.returncode, result.stdout, result.stderr) == (0, "", "")


@pytest.mark.parametrize("args", [[], ["on-edit"]])
def test_unknown_subcommand_prints_usage(args: list[str]) -> None:
    """Broken wiring is visible: usage on stderr, exit 2 (design D3)."""
    result = _run(args, _write("/home/u/.claude/projects/slug/memory/fact.md"))
    assert result.returncode == 2
    assert "usage" in result.stderr
