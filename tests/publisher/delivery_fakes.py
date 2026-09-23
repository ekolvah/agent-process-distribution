"""Fakes of the delivery-script tests: the script loader and the fake `gh`."""

from __future__ import annotations

import importlib
import importlib.util
import json
import sys
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
    ]
}


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
    that raises as `run_gh` does on a non-zero exit.
    """

    def __init__(
        self,
        *,
        projects: list[dict] | None = None,
        status: str | None = "Planned",
        other_items: list[tuple[str, str]] = (),
        fail_on: list[str] | None = None,
        remote_branch: bool = False,
    ) -> None:
        self.calls: list[list[str]] = []
        self.projects = [PROJECT] if projects is None else projects
        self.status = status
        self.other_items = list(other_items)
        self.fail_on = fail_on
        self.remote_branch = remote_branch

    def __call__(self, cmd: list[str]) -> str:  # noqa: C901, PLR0911, PLR0912 -- baseline: fake gh answers one branch per command shape
        self.calls.append(cmd)
        head = cmd[:3]
        if self.fail_on is not None and cmd[: len(self.fail_on)] == self.fail_on:
            raise RuntimeError(f"`{' '.join(cmd)}` failed (rc=1): boom")
        if head == ["git", "ls-remote", "--heads"]:
            return f"0123abcd\trefs/heads/{cmd[-1]}\n" if self.remote_branch else ""
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
            return json.dumps(FIELDS)
        if head == ["gh", "project", "item-add"]:
            return json.dumps({"id": "PVTI_7"})
        if head == ["gh", "project", "item-edit"]:
            return ""
        raise AssertionError(f"unexpected gh call: {cmd}")

    def edits(self) -> list[list[str]]:
        return [c for c in self.calls if c[:3] == ["gh", "project", "item-edit"]]
