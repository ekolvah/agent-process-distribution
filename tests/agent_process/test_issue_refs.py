"""The `no-issue-refs` hook keeps issue and PR references in the history records.

Each test runs the repository's own hook definition in a temporary repository, so a change
to its expression, `exclude` or `types` reaches the tests. Offending literals are built
through f-strings: the hook scans this file too.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import yaml

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_HOOK_ID = "no-issue-refs"


def _hook() -> dict[str, object]:
    config = yaml.safe_load((_REPO_ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8"))
    hooks = [hook for repo in config["repos"] for hook in repo["hooks"] if hook["id"] == _HOOK_ID]
    assert hooks, f"`.pre-commit-config.yaml` declares no hook `{_HOOK_ID}`"
    return hooks[0]


def _run_hook(tmp_path: Path, files: dict[str, str]) -> tuple[int, str]:
    """Exit code and output of the hook over `files` in a fresh repository."""
    hook = _hook()
    config = {"repos": [{"repo": "local", "hooks": [hook]}]}
    (tmp_path / ".pre-commit-config.yaml").write_text(yaml.safe_dump(config), encoding="utf-8")
    for name, text in files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    result = subprocess.run(
        [sys.executable, "-m", "pre_commit", "run", "--all-files", "--hook-stage", "pre-commit"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.returncode, f"{result.stdout}{result.stderr}"


def test_issue_reference_outside_history(tmp_path: Path) -> None:
    offenders = {
        "skills/agent-process/scripts/comment.py": f"x = 1  # fixed (issue {349})\n",
        "skills/agent-process/scripts/docstring.py": f'"""Reads the rules (#{348})."""\n',
        ".github/workflows/wrapped.yml": f"# a step the review skipped (issue\n# {139})\n",
        ".claude/rules/wrapped.md": f"The guard holds (issue\n{112}).\n",
        "tests/pr.py": f"# round two of PR {147}\n",
        "tests/pull_request.py": f"# as pull request {352} showed\n",
        "skills/agent-process/SKILL.md": f"See issue #{97}.\n",
    }
    code, output = _run_hook(tmp_path, offenders)
    assert code == 1, output
    missed = [name for name in offenders if name not in output]
    assert not missed, f"not reported: {missed}\n{output}"


def test_history_record_keeps_its_references(tmp_path: Path) -> None:
    history = f"Decided in #{353}, see issue {349}.\n"
    files = {
        ".agent-process/docs/adr/0001-x.md": history,
        "CHANGELOG.md": history,
        "openspec/changes/x/proposal.md": history,
        "openspec/changes/archive/2026-01-01-x/design.md": history,
        "docs/other.md": "`&#123;`, pull/5#x, #doc-guards, C#1 and `Closes #<N>`.\n",
    }
    code, output = _run_hook(tmp_path, files)
    assert code == 0, output
