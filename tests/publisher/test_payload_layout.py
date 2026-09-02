"""RED contracts for the single-root consumer payload layout (issue #55)."""

from __future__ import annotations

import re
from pathlib import Path

from test_project_bootstrap_template import render

from scripts.adopt_agent_process import _CLOSED_ROOT_FILES, _CLOSED_ROOT_PREFIXES


def _is_closed_root_path(relative: str) -> bool:
    return relative in _CLOSED_ROOT_FILES or relative.startswith(_CLOSED_ROOT_PREFIXES)


def _files(directory: Path) -> set[str]:
    return {
        path.relative_to(directory).as_posix()
        for path in directory.rglob("*")
        if path.is_file() and path.as_posix() != ".agent-process/copier-answers.yml"
    }


def test_rendered_payload_is_confined_to_the_single_root(tmp_path: Path) -> None:
    """Every non-tool-mandated rendered path must live under .agent-process/."""
    rendered = render(tmp_path)

    escaped = sorted(
        relative
        for relative in _files(rendered)
        if not relative.startswith(".agent-process/") and not _is_closed_root_path(relative)
    )

    assert not escaped


def test_rendered_commands_use_the_process_root(tmp_path: Path) -> None:
    rendered = render(tmp_path)
    stale = []
    for path in rendered.rglob("*"):
        if not path.is_file() or path.suffix not in {".md", ".py", ".yml", ".yaml"}:
            continue
        text = path.read_text(encoding="utf-8")
        if "python scripts/" in text or re.search(r"(?<!\.agent-process/)docs/architecture/", text):
            stale.append(path.relative_to(rendered).as_posix())

    assert not stale
