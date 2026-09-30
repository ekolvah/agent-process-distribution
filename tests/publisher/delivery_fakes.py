"""Fakes of the delivery-script tests: the script loader and the fake `gh`."""

from __future__ import annotations

import importlib
import importlib.util
import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SKILL_SCRIPTS = ROOT / "skills" / "agent-process" / "scripts"
PROJECT = {"id": "PVT_1", "number": 4, "title": "Board", "resourcePath": "/users/owner/projects/4"}
FIELDS = {
    "fields": [
        {
            "id": "F_STATUS",
            "name": "Status",
            "type": "ProjectV2SingleSelectField",
            "options": [
                {"id": "S_TODO", "name": "Todo"},
                {"id": "S_PLAN", "name": "Planned"},
                {"id": "S_PROG", "name": "In Progress"},
            ],
        },
        {
            "id": "F_PRIO",
            "name": "Priority",
            "type": "ProjectV2SingleSelectField",
            "options": [{"id": "P_HIGH", "name": "High"}, {"id": "P_LOW", "name": "Low"}],
        },
        {
            "id": "F_AREA",
            "name": "Area",
            "type": "ProjectV2SingleSelectField",
            "options": [
                {"id": "A_OBS", "name": "Observability"},
                {"id": "A_DIST", "name": "Distribution"},
                {"id": "A_TOK", "name": "Token efficiency"},
            ],
        },
    ]
}
NO_AREA = {"fields": [f for f in FIELDS["fields"] if f["name"] != "Area"]}


def load_script(name: str) -> Any:
    path = SKILL_SCRIPTS / f"{name}.py"
    if path.is_file():
        module_name = f"agent_process_skill_{name}"
        if module_name in sys.modules:
            return sys.modules[module_name]
        spec = importlib.util.spec_from_file_location(module_name, path)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        sys.path.insert(0, str(SKILL_SCRIPTS))
        try:
            spec.loader.exec_module(module)
        finally:
            sys.path.remove(str(SKILL_SCRIPTS))
        return module
    return importlib.import_module(f"scripts.{name}")


class Gh:
    """Fake `gh`: answers by command shape, records every call.

    `status` is what `gh issue view --json projectItems` reports for the issue on the
    linked Project (`None`: the issue is no item of it); `other_items` are the issue's items
    on other Projects, `(title, status)` each, listed first; `fail_on` is a command head
    that raises as `run_gh` does on a non-zero exit; `fields` is what `field-list` prints.
    `root` is the main worktree `git worktree list --porcelain` lists, followed by one
    clean worktree per branch of `extra_worktrees` under its `.claude/worktrees/`;
    `pr_states` answers `gh pr view <branch> --json state` (an absent branch raises as
    `run_gh` does on `no pull requests found`); `git_runner`, when given, runs every `git`
    command and `gh issue develop` pushes the branch through it.
    """

    def __init__(  # noqa: PLR0913 -- keyword-only fake knobs, one per gh answer
        self,
        *,
        projects: list[dict] | None = None,
        status: str | None = "Planned",
        other_items: list[tuple[str, str]] = (),
        fail_on: list[str] | None = None,
        remote_branch: bool = False,
        fields: dict | None = None,
        root: Path | None = None,
        extra_worktrees: list[str] = (),
        pr_states: dict[str, str] | None = None,
        git_runner: Callable[[list[str]], str] | None = None,
    ) -> None:
        self.calls: list[list[str]] = []
        self.projects = [PROJECT] if projects is None else projects
        self.status = status
        self.other_items = list(other_items)
        self.fail_on = fail_on
        self.remote_branch = remote_branch
        self.fields = FIELDS if fields is None else fields
        self.root = root
        self.extra_worktrees = list(extra_worktrees)
        self.pr_states = pr_states or {}
        self.git_runner = git_runner

    def _listing(self) -> str:
        """What `git worktree list --porcelain` prints: forward slashes, a blank line after
        each entry, the main worktree first."""
        assert self.root is not None, "the fake lists worktrees of `root` only"
        entries = [(self.root, "main")] + [
            (self.root / ".claude" / "worktrees" / b, b) for b in self.extra_worktrees
        ]
        return "".join(
            f"worktree {path.as_posix()}\nHEAD 0123abcd\nbranch refs/heads/{branch}\n\n"
            for path, branch in entries
        )

    def __call__(self, cmd: list[str]) -> str:  # noqa: C901, PLR0911, PLR0912 -- baseline: fake gh answers one branch per command shape
        self.calls.append(cmd)
        head = cmd[:3]
        if self.fail_on is not None and cmd[: len(self.fail_on)] == self.fail_on:
            raise RuntimeError(f"`{' '.join(cmd)}` failed (rc=1): boom")
        if cmd[0] == "git" and self.git_runner is not None:
            return self.git_runner(cmd)
        if head == ["git", "ls-remote", "--heads"]:
            return f"0123abcd\trefs/heads/{cmd[-1]}\n" if self.remote_branch else ""
        if head in (["git", "fetch", "origin"], ["git", "worktree", "add"]):
            return ""
        if cmd == ["git", "worktree", "list", "--porcelain"]:
            return self._listing()
        if cmd[:2] == ["git", "-C"] and cmd[3:] == ["status", "--porcelain"]:
            return ""
        if cmd[:2] == ["git", "-C"] and cmd[3] in ("add", "commit"):
            return ""
        if head == ["git", "worktree", "remove"]:
            return ""
        if head == ["gh", "pr", "view"]:
            if cmd[3] not in self.pr_states:
                raise RuntimeError(
                    f'`{" ".join(cmd)}` failed (rc=1): no pull requests found for branch "{cmd[3]}"'
                )
            return json.dumps({"state": self.pr_states[cmd[3]]})
        if head == ["gh", "issue", "view"] and "projectItems" in cmd:
            # The shape `gh issue view 144 --json projectItems` printed: `title` is the
            # Project's title, one entry per Project the issue is an item of (v2-2f).
            items = [(t, s) for t, s in self.other_items]
            if self.status is not None:
                items.append((PROJECT["title"], self.status))
            return json.dumps(
                {
                    "projectItems": [
                        {"status": {"optionId": "S_X", "name": s}, "title": t} for t, s in items
                    ]
                }
            )
        if head == ["gh", "issue", "develop"]:
            if self.git_runner is not None:
                name = cmd[cmd.index("--name") + 1]
                self.git_runner(["git", "push", "origin", f"main:refs/heads/{name}"])
            return "github.com/owner/repo/tree/branch\n"
        if head == ["gh", "issue", "comment"]:
            return "https://github.com/owner/repo/issues/7#issuecomment-1\n"
        if head == ["gh", "issue", "create"]:
            return "https://github.com/owner/repo/issues/7\n"
        if head == ["gh", "repo", "view"]:
            # `Nodes` with a capital N is what gh 2.87.3 prints for `--json projectsV2`.
            return json.dumps(
                {
                    "owner": {"login": "owner"},
                    "name": "repo",
                    "projectsV2": {"Nodes": self.projects},
                }
            )
        if head == ["gh", "issue", "view"]:
            return json.dumps({"url": "https://github.com/owner/repo/issues/7"})
        if head == ["gh", "api", "graphql"]:
            raise AssertionError("set_status must read the linked Project with gh repo view")
        if head == ["gh", "project", "field-list"]:
            return json.dumps(self.fields)
        if head == ["gh", "project", "item-add"]:
            return json.dumps({"id": "PVTI_7"})
        if head == ["gh", "project", "item-edit"]:
            return ""
        raise AssertionError(f"unexpected gh call: {cmd}")

    def edits(self) -> list[list[str]]:
        return [c for c in self.calls if c[:3] == ["gh", "project", "item-edit"]]
