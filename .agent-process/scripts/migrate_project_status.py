#!/usr/bin/env python3
"""Report or migrate legacy ``Agent status`` values into built-in ``Status``.

The default is deliberately read-only.  ``--confirm-write`` is required for
remote option/item updates; deleting the old field is a separate confirmation.
"""

from __future__ import annotations

import argparse
import importlib
import json
import subprocess
import sys
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class MigrationPlan:
    status_field_id: str
    legacy_field_id: str
    option_update: dict[str, object] | None
    item_updates: tuple[tuple[str, str], ...]
    preserved_item_ids: tuple[str, ...]
    view_dependencies: tuple[str, ...]
    delete_legacy_allowed: bool
    settings_write_after_verification: bool = True
    partial_failure_is_visible: bool = True


def _field(fields: object, name: str) -> dict[str, Any]:
    if not isinstance(fields, list):
        raise ValueError("Project fields must be a list")
    matches = [field for field in fields if isinstance(field, dict) and field.get("name") == name]
    if len(matches) != 1 or not matches[0].get("id"):
        raise ValueError(f"Project needs exactly one {name!r} field")
    return matches[0]


def _option_id(field: dict[str, Any], name: str) -> str | None:
    for option in field.get("options", []):
        if isinstance(option, dict) and str(option.get("name", "")).casefold() == name.casefold():
            value = option.get("id")
            return str(value) if value else None
    return None


def build_plan(fields: object, items: object, views: object) -> MigrationPlan:
    """Build a pure, idempotent plan from already-read Project data."""
    status = _field(fields, "Status")
    legacy = _field(fields, "Agent status")
    options = status.get("options")
    if not isinstance(options, list):
        raise ValueError("built-in Status options are unreadable")
    planned = _option_id(status, "Planned")
    preserved_options: list[dict[str, object]] = []
    for option in options:
        if not isinstance(option, dict) or not all(key in option for key in ("id", "name", "color", "description")):
            raise ValueError("Status option lacks id/name/color/description; refusing replacement")
        preserved_options.append({key: option[key] for key in ("id", "name", "color", "description")})
    option_update: dict[str, object] | None = None
    if planned is None:
        preserved_options.append({"name": "Planned", "color": "BLUE", "description": ""})
        option_update = {"fieldId": str(status["id"]), "singleSelectOptions": preserved_options}

    updates: list[tuple[str, str]] = []
    preserved: list[str] = []
    if not isinstance(items, list):
        raise ValueError("Project items must be a list")
    for item in items:
        if not isinstance(item, dict) or not item.get("id"):
            raise ValueError("Project item lacks an id")
        current = str(item.get("status") or "")
        legacy_value = str(item.get("agent status") or "")
        if current.casefold() == "done" and legacy_value:
            preserved.append(str(item["id"]))
        elif legacy_value.casefold() == "planned" and current.casefold() != "planned":
            updates.append((str(item["id"]), "planned"))
        elif legacy_value.casefold() == "in progress" and current.casefold() != "in progress":
            updates.append((str(item["id"]), "progress"))

    dependencies: list[str] = []
    if not isinstance(views, list):
        raise ValueError("Project views must be a list")
    for view in views:
        if isinstance(view, dict) and str(legacy["id"]) in view.get("fields", []):
            dependencies.append(str(view.get("name") or view.get("id") or "unnamed view"))
    return MigrationPlan(
        status_field_id=str(status["id"]),
        legacy_field_id=str(legacy["id"]),
        option_update=option_update,
        item_updates=tuple(updates),
        preserved_item_ids=tuple(preserved),
        view_dependencies=tuple(dependencies),
        delete_legacy_allowed=False,
    )


def _graphql(query: str, variables: dict[str, object]) -> dict[str, Any]:
    completed = subprocess.run(
        ["gh", "api", "graphql", "--input", "-"], input=json.dumps({"query": query, "variables": variables}),
        text=True, capture_output=True, encoding="utf-8"
    )
    if completed.stdout is None or completed.stderr is None:
        raise RuntimeError("gh api graphql output capture failed")
    if completed.returncode:
        raise RuntimeError(completed.stderr.strip() or "gh api graphql failed")
    payload = json.loads(completed.stdout)
    if not isinstance(payload, dict) or payload.get("errors"):
        raise RuntimeError(f"gh api graphql returned errors: {payload.get('errors')!r}")
    return payload


def _configured_project() -> tuple[str, str, str]:
    try:
        from . import project_settings
    except ImportError:
        import project_settings
    project_settings = importlib.reload(project_settings)
    project_settings.require_configured()
    return project_settings.PROJECT_ID, project_settings.PROJECT_NUMBER, project_settings.PROJECT_OWNER


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirm-write", action="store_true")
    parser.add_argument("--delete-agent-status", action="store_true")
    ns = parser.parse_args(argv)
    try:
        project_id, _, _ = _configured_project()
        query = """query($project: ID!) { node(id: $project) { ... on ProjectV2 { fields(first: 100) { nodes { ... on ProjectV2SingleSelectField { id name options { id name color description } } } } items(first: 100) { nodes { id fieldValues(first: 100) { nodes { ... on ProjectV2ItemFieldSingleSelectValue { name field { ... on ProjectV2SingleSelectField { id name } } } } } } } views(first: 100) { nodes { id name configuration { visibleFields(first: 100) { nodes { ... on ProjectV2SingleSelectField { id } } } } } } } } }"""
        data = _graphql(query, {"project": project_id})["data"]["node"]
        fields = data["fields"]["nodes"]
        values = data["items"]["nodes"]
        items = []
        for item in values:
            row: dict[str, object] = {"id": item["id"], "status": "", "agent status": ""}
            for value in item["fieldValues"]["nodes"]:
                field = value.get("field") if isinstance(value, dict) else None
                if isinstance(field, dict) and field.get("name") == "Status":
                    row["status"] = value.get("name") or ""
                if isinstance(field, dict) and field.get("name") == "Agent status":
                    row["agent status"] = value.get("name") or ""
            items.append(row)
        views = [
            {"name": view["name"], "fields": [field["id"] for field in view["configuration"]["visibleFields"]["nodes"]]}
            for view in data["views"]["nodes"]
        ]
        plan = build_plan(fields, items, views)
        print(json.dumps({"option_update": plan.option_update, "item_updates": plan.item_updates, "preserved_done": plan.preserved_item_ids, "view_dependencies": plan.view_dependencies}, indent=2))
        if not ns.confirm_write:
            return
        if ns.delete_agent_status:
            raise RuntimeError("legacy-field deletion requires a separately verified, view-free report")
        if plan.option_update:
            mutation = """mutation($input: UpdateProjectV2FieldInput!) { updateProjectV2Field(input: $input) { projectV2Field { ... on ProjectV2SingleSelectField { id } } } }"""
            _graphql(mutation, {"input": plan.option_update})
        print("ok: option/item migration requires a fresh postcondition capture before settings are written")
    except (KeyError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
