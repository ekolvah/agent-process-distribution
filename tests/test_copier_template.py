"""Render-level contracts for the optional GitHub Project adapter."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def render(tmp_path: Path, *answers: str) -> Path:
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
            *answers,
        ],
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    return destination


def rendered_text(destination: Path) -> str:
    return "\n".join(
        path.read_text(encoding="utf-8")
        for path in destination.rglob("*")
        if path.is_file() and ".git" not in path.parts
    )


def initialize_repository(destination: Path) -> None:
    for command in (["git", "init"], ["git", "add", "--all"]):
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


def generated_tests_pass(destination: Path) -> None:
    suite = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=destination,
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    assert suite.returncode == 0, suite.stdout + suite.stderr


def test_default_render_omits_the_github_project_adapter(tmp_path: Path) -> None:
    destination = render(tmp_path)
    initialize_repository(destination)

    priority_script = (destination / "scripts" / "set_issue_priority.py").read_text(
        encoding="utf-8"
    )
    status_script = (destination / "scripts" / "set_issue_status.py").read_text(
        encoding="utf-8"
    )
    assert "integration is disabled" in priority_script
    assert "integration is disabled" in status_script
    assert "subprocess" not in priority_script
    assert "subprocess" not in status_script
    payload = rendered_text(destination)
    assert "PVT_" not in payload
    assert "REPLACE_ME" not in payload
    assert "{%" not in payload
    assert "set_issue_priority.py" not in (destination / "AGENTS.md").read_text(
        encoding="utf-8"
    )
    assert "set_issue_status.py" not in (
        destination / "docs" / "architecture" / "agent-process.md"
    ).read_text(encoding="utf-8")

    compiled = subprocess.run(
        [sys.executable, "-m", "compileall", "-q", "scripts"],
        cwd=destination,
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    assert compiled.returncode == 0, compiled.stdout + compiled.stderr

    generated_tests_pass(destination)


def test_project_render_keeps_the_parameterized_adapter(tmp_path: Path) -> None:
    destination = render(
        tmp_path,
        "--data",
        "github_project_enabled=true",
        "--data",
        "github_project_number=27",
        "--data",
        "github_project_owner=example-org",
        "--data",
        "github_project_id=PVT_project_27",
        "--data",
        "priority_field_id=PVTSSF_priority_27",
        "--data",
        "priority_option_high=priority_high_27",
        "--data",
        "priority_option_medium=priority_medium_27",
        "--data",
        "priority_option_low=priority_low_27",
        "--data",
        "status_field_id=PVTSSF_status_27",
        "--data",
        "status_option_planned=status_planned_27",
        "--data",
        "status_option_in_progress=status_in_progress_27",
    )

    priority_script = (destination / "scripts" / "set_issue_priority.py").read_text(
        encoding="utf-8"
    )
    status_script = (destination / "scripts" / "set_issue_status.py").read_text(
        encoding="utf-8"
    )
    assert 'PROJECT_NUMBER = "27"' in priority_script
    assert 'PROJECT_OWNER = "example-org"' in priority_script
    assert 'PROJECT_ID = "PVT_project_27"' in priority_script
    assert 'PRIORITY_FIELD_ID = "PVTSSF_priority_27"' in priority_script
    assert '"high": "priority_high_27"' in priority_script
    assert '"medium": "priority_medium_27"' in priority_script
    assert '"low": "priority_low_27"' in priority_script
    assert 'STATUS_FIELD_ID = "PVTSSF_status_27"' in status_script
    assert '"planned": "status_planned_27"' in status_script
    assert '"in-progress": "status_in_progress_27"' in status_script
    assert "set_issue_priority.py N --check" in (destination / "AGENTS.md").read_text(
        encoding="utf-8"
    )
    initialize_repository(destination)
    generated_tests_pass(destination)
