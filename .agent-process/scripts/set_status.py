#!/usr/bin/env python3
"""Set an issue's Status and/or Priority in the repository's GitHub Project by name.

Usage: python .agent-process/scripts/set_status.py <N> ["<Status>"] [--priority "<Priority>"]

The process writes two Statuses: "Planned" at the end of the propose run and "In Progress"
at the start of the apply; "Todo" and "Done" are the Project's own workflows. The Project is
the single one linked to the repository; field and option ids are resolved from their names
on every run, so no generated settings file is needed. Exit 2 when neither field is given,
when a name does not resolve (the options are listed; nothing is changed) or when zero or
several Projects are linked (they are named); exit 1 when `gh` fails.

The `gh project` helpers are duplicated from `set_issue_status.py` / `set_issue_priority.py`
on purpose: those scripts and their `project_settings.py` are deleted in `v2-4`, and this
survivor must not import what dies. Delete the duplication when they are gone.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Callable
from typing import Any

Gh = Callable[[list[str]], str]


def run_gh(cmd: list[str]) -> str:
    """Run `gh`; a non-zero exit raises with the captured stderr (visible failure)."""
    result = subprocess.run(cmd, text=True, capture_output=True, encoding="utf-8")
    if result.stdout is None or result.stderr is None:
        raise RuntimeError(f"`{' '.join(cmd)}`: broken capture (stdout or stderr is None)")
    if result.returncode != 0:
        detail = result.stderr.strip() or "no stderr"
        raise RuntimeError(f"`{' '.join(cmd)}` failed (rc={result.returncode}): {detail}")
    return result.stdout


def _json(gh: Gh, cmd: list[str]) -> Any:
    out = gh(cmd)
    try:
        return json.loads(out)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"`{' '.join(cmd)}` returned no JSON: {out!r}") from exc


def _repo(gh: Gh) -> tuple[str, str, list[dict[str, Any]]]:
    """Owner, name and the Projects linked to the repository (gh prints them under `Nodes`)."""
    data = _json(gh, ["gh", "repo", "view", "--json", "owner,name,projectsV2"])
    linked = data.get("projectsV2") or {}
    projects = linked.get("Nodes", linked.get("nodes")) or []
    return str(data["owner"]["login"]), str(data["name"]), list(projects)


def _linked_project(owner: str, name: str, projects: list[dict[str, Any]]) -> dict[str, Any]:
    """The board is the one Project linked to the repository; zero or several is an error."""
    if len(projects) == 1:
        return projects[0]
    named = ", ".join(f"#{p['number']} {p['title']}" for p in projects) or "none linked"
    raise ValueError(
        f"expected exactly one Project linked to {owner}/{name}, found: {named}; "
        "link the board (repository → Projects) and unlink the rest"
    )


def _issue_url(gh: Gh, number: int) -> str:
    data = _json(gh, ["gh", "issue", "view", str(number), "--json", "url"])
    return str(data["url"])


def _fields(gh: Gh, owner: str, project: dict[str, Any]) -> dict[str, dict[str, Any]]:
    data = _json(
        gh,
        [
            "gh",
            "project",
            "field-list",
            str(project["number"]),
            "--owner",
            owner,
            "--format",
            "json",
        ],
    )
    return {str(f["name"]): f for f in data["fields"]}


def _option_id(fields: dict[str, dict[str, Any]], field_name: str, option_name: str) -> str:
    field = fields.get(field_name)
    if field is None:
        raise ValueError(f"no field {field_name!r} in the Project; fields: {', '.join(fields)}")
    options = {str(o["name"]): str(o["id"]) for o in field.get("options") or []}
    try:
        return options[option_name]
    except KeyError:
        raise ValueError(
            f"unknown {field_name} option {option_name!r}; options: {', '.join(options)}"
        ) from None


def _item_add(gh: Gh, owner: str, project: dict[str, Any], url: str) -> str:
    """`item-add` on an issue that is already an item returns the same item id (exit 0)."""
    data = _json(
        gh,
        [
            "gh",
            "project",
            "item-add",
            str(project["number"]),
            "--owner",
            owner,
            "--url",
            url,
            "--format",
            "json",
        ],
    )
    item_id = data.get("id")
    if not item_id:
        raise RuntimeError(f"`gh project item-add` returned no item id: {data!r}")
    return str(item_id)


def _item_edit(gh: Gh, project_id: str, item_id: str, field_id: str, option_id: str) -> None:
    gh(
        [
            "gh",
            "project",
            "item-edit",
            "--id",
            item_id,
            "--field-id",
            field_id,
            "--project-id",
            project_id,
            "--single-select-option-id",
            option_id,
        ]
    )


def set_status(
    number: int, status: str | None = None, *, priority: str | None = None, gh: Gh = run_gh
) -> None:
    """Set Status and/or Priority of issue `number`; every name resolves before any write."""
    if status is None and priority is None:
        raise ValueError("nothing to set: give a Status, --priority, or both")
    owner, name, projects = _repo(gh)
    project = _linked_project(owner, name, projects)
    fields = _fields(gh, owner, project)
    writes = []
    if status is not None:
        writes.append((str(fields["Status"]["id"]), _option_id(fields, "Status", status)))
    if priority is not None:
        writes.append((str(fields["Priority"]["id"]), _option_id(fields, "Priority", priority)))
    item_id = _item_add(gh, owner, project, _issue_url(gh, number))
    for field_id, option_id in writes:
        _item_edit(gh, str(project["id"]), item_id, field_id, option_id)


def main(argv: list[str] | None = None, *, gh: Gh = run_gh) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("issue", type=int, help="issue number")
    parser.add_argument("status", nargs="?", help='Status option name: "Planned" or "In Progress"')
    parser.add_argument("--priority", help='Priority option name, e.g. "High"')
    ns = parser.parse_args(argv)
    try:
        set_status(ns.issue, ns.status, priority=ns.priority, gh=gh)
    except (KeyError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(2)
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)
    done = [f"status {ns.status}"] if ns.status else []
    if ns.priority:
        done.append(f"priority {ns.priority}")
    print(f"ok: issue #{ns.issue} {', '.join(done)}")


if __name__ == "__main__":
    main()
