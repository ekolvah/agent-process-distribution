"""Render contracts for required GitHub Project bootstrap modes."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest


ROOT = Path(__file__).resolve().parents[1]


def render(tmp_path: Path, *data: str) -> Path:
    destination = tmp_path / "rendered"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "copier",
            "copy",
            str(ROOT),
            str(destination),
            "--vcs-ref",
            "HEAD",
            "--defaults",
            "--trust",
            *data,
        ],
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    return destination


def bootstrap_module(destination: Path) -> ModuleType:
    path = destination / "scripts" / "bootstrap_github_project.py"
    spec = importlib.util.spec_from_file_location("bootstrap_github_project", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(path.parent))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.pop(0)
    return module


def generated_suite_passes(destination: Path) -> None:
    for command in (
        ["git", "init"],
        ["git", "add", "--all"],
        [sys.executable, "-m", "pytest", "-q"],
    ):
        completed = subprocess.run(
            command,
            cwd=destination,
            text=True,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        assert completed.returncode == 0, completed.stdout + completed.stderr


def test_create_mode_requires_explicit_confirmation_and_no_placeholder_ids(
    tmp_path: Path,
) -> None:
    destination = render(
        tmp_path, "--data", "github_repository=example-org/example-repo"
    )

    settings = (destination / "scripts" / "project_settings.py").read_text(
        encoding="utf-8"
    )
    assert "PVT_" not in settings
    assert "REPLACE_ME" not in settings
    bootstrap = destination / "scripts" / "bootstrap_github_project.py"
    completed = subprocess.run(
        [sys.executable, str(bootstrap)],
        cwd=destination,
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    assert completed.returncode == 2
    assert "--confirm-create" in completed.stderr
    generated_suite_passes(destination)


def test_existing_mode_bakes_only_the_selected_project_number(tmp_path: Path) -> None:
    destination = render(
        tmp_path,
        "--data",
        "github_project_mode=existing",
        "--data",
        "github_project_owner=example-org",
        "--data",
        "existing_github_project_number=42",
    )

    bootstrap = (destination / "scripts" / "bootstrap_github_project.py").read_text(
        encoding="utf-8"
    )
    assert 'MODE = "existing"' in bootstrap
    assert 'OWNER = "example-org"' in bootstrap
    assert 'EXISTING_NUMBER = "42"' in bootstrap
    assert "--confirm-create" not in (destination / "AGENTS.md").read_text(
        encoding="utf-8"
    )


def test_create_mode_links_fields_and_persists_real_ids(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = render(
        tmp_path, "--data", "github_repository=example-org/example-repo"
    )
    bootstrap = bootstrap_module(destination)
    calls: list[list[str]] = []
    fields = {
        "fields": [
            {
                "id": "priority-field",
                "name": "Priority",
                "options": [
                    {"id": "priority-high", "name": "High"},
                    {"id": "priority-medium", "name": "Medium"},
                    {"id": "priority-low", "name": "Low"},
                ],
            },
            {
                "id": "status-field",
                "name": "Agent status",
                "options": [
                    {"id": "status-planned", "name": "Planned"},
                    {"id": "status-progress", "name": "In Progress"},
                ],
            },
        ]
    }

    def fake_run(command: list[str]) -> dict[str, object]:
        calls.append(command)
        if command[2] == "create":
            return {"number": 7, "id": "project-7"}
        if command[2] == "field-list":
            return fields
        return {}

    monkeypatch.setattr(bootstrap, "_run", fake_run)
    monkeypatch.setattr(
        bootstrap, "_checked", lambda command: calls.append(command) or ""
    )

    bootstrap.main(["--confirm-create"])

    settings = (destination / "scripts" / "project_settings.py").read_text(
        encoding="utf-8"
    )
    assert "PROJECT_NUMBER = '7'" in settings
    assert "PROJECT_ID = 'project-7'" in settings
    assert "priority-high" in settings
    assert "status-progress" in settings
    assert [
        "gh",
        "project",
        "link",
        "7",
        "--owner",
        "@me",
        "--repo",
        "example-org/example-repo",
    ] in calls
