"""A git repository with a `.pre-commit-config.yaml` of local hooks, for the edit-time lint tests."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from tests.publisher.init_harness import git


def _hook(hook_id: str, code: str, stage: str, *, pass_filenames: bool = True) -> dict:
    """A local hook running `code` in this interpreter, quoted as `conftest.py` does."""
    return {
        "id": hook_id,
        "name": hook_id,
        # The interpreter is quoted: pre-commit splits the entry, and its path may hold a space.
        "entry": f'"{Path(sys.executable).as_posix()}" -c "{code}"',
        "language": "unsupported",
        "stages": [stage],
        "pass_filenames": pass_filenames,
        "always_run": not pass_filenames,
    }


FINDING = _hook(
    "finding", "import sys; print('finding:', *sys.argv[1:]); sys.exit(1)", "pre-commit"
)
PRE_PUSH = _hook("pushed", "open('ran', 'w').close()", "pre-push", pass_filenames=False)


def lint_repo(root: Path, *hooks: dict) -> Path:
    """A git repository with `a.py` and a config of `hooks`; no config when none are given."""
    root.mkdir(parents=True, exist_ok=True)
    git("init", "-q", str(root))
    (root / "a.py").write_text("a = 1\n", encoding="utf-8")
    if hooks:
        config = {
            "default_install_hook_types": ["pre-push"],
            "repos": [{"repo": "local", "hooks": list(hooks)}],
        }
        (root / ".pre-commit-config.yaml").write_text(json.dumps(config), encoding="utf-8")
    git("add", "-A", cwd=root)
    return root


def edit_payload(path: Path) -> dict:
    """An `Edit` PostToolUse payload for `path`."""
    return {"tool_name": "Edit", "tool_input": {"file_path": path.as_posix()}}
