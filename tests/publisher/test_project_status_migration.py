"""RED contract for built-in Project Status migration (#86)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def migration_module():
    path = ROOT / ".agent-process" / "scripts" / "migrate_project_status.py"
    spec = importlib.util.spec_from_file_location("migrate_project_status", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(spec.name, None)
    return module


FIELDS = [
    {"id": "status", "name": "Status", "options": [
        {"id": "todo", "name": "Todo", "color": "GRAY", "description": ""},
        {"id": "progress", "name": "In Progress", "color": "YELLOW", "description": ""},
        {"id": "done", "name": "Done", "color": "GREEN", "description": ""},
    ]},
    {"id": "agent", "name": "Agent status", "options": [
        {"id": "legacy-planned", "name": "Planned"},
        {"id": "legacy-progress", "name": "In Progress"},
    ]},
]
ITEMS = [
    {"id": "planned-item", "status": "Todo", "agent status": "Planned"},
    {"id": "progress-item", "status": "Todo", "agent status": "In Progress"},
    {"id": "done-item", "status": "Done", "agent status": "In Progress"},
]


class TestMigrationPlan:
    def test_default_report_is_read_only_and_lists_field_item_and_view_actions(self) -> None:
        plan = migration_module().build_plan(FIELDS, ITEMS, [{"name": "Board", "fields": ["agent"]}])
        assert plan.option_update["singleSelectOptions"][-1]["name"] == "Planned"
        assert plan.item_updates == (("planned-item", "planned"), ("progress-item", "progress"))
        assert plan.view_dependencies == ("Board",)


class TestMigrationApply:
    def test_confirmed_migration_preserves_done_and_converges_on_rerun(self) -> None:
        plan = migration_module().build_plan(FIELDS, ITEMS, [])
        assert plan.preserved_item_ids == ("done-item",)
        assert plan.item_updates == (("planned-item", "planned"), ("progress-item", "progress"))

    def test_partial_remote_failure_keeps_settings_and_reports_progress(self) -> None:
        plan = migration_module().build_plan(FIELDS, ITEMS, [])
        assert plan.settings_write_after_verification is True
        assert plan.partial_failure_is_visible is True

    def test_settings_write_follows_verified_items(self) -> None:
        assert migration_module().build_plan(FIELDS, ITEMS, []).status_field_id == "status"


class TestLegacyFieldRetirement:
    def test_deletion_requires_confirmation_and_a_view_free_verified_report(self) -> None:
        assert migration_module().build_plan(FIELDS, ITEMS, [{"name": "Board", "fields": ["agent"]}]).delete_legacy_allowed is False
