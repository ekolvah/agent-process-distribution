"""Render contracts for required GitHub Project bootstrap modes."""

from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]


def render(tmp_path: Path, *data: str) -> Path:
    """Render a deliberately non-default answer set for mode-specific coverage."""
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


def _workflow(path: Path) -> dict[object, object]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_rendered_project_ships_thin_required_context_callers(rendered_default: Path) -> None:
    destination = rendered_default
    answers = yaml.safe_load((destination / ".copier-answers.yml").read_text(encoding="utf-8"))
    workflows = destination / ".github" / "workflows"
    contexts = tuple(answers["required_status_contexts"])

    assert {"ci.yml", "pr-link.yml", "agent-review.yml"} <= {p.name for p in workflows.iterdir()}
    for context, filename in zip(
        contexts, ("ci.yml", "pr-link.yml", "agent-review.yml"), strict=True
    ):
        job_key = context.split(" / ", 1)[0]
        job = _workflow(workflows / filename)["jobs"][job_key]
        assert "uses" in job
        if job_key == "quality":
            assert "with" not in job
        assert job_key == context.split(" / ", 1)[0]


def test_rendered_project_ships_the_standalone_review_contract(rendered_default: Path) -> None:
    destination = rendered_default

    assert (destination / "REVIEW_CONTRACT.md").is_file()
    assert "[REVIEW_CONTRACT.md](REVIEW_CONTRACT.md)" in (destination / "AGENTS.md").read_text(
        encoding="utf-8"
    )
    assert not (destination / "scripts" / "extract_review_prompt.py").exists()


def test_rendered_callers_pin_a_complete_reference_and_map_secrets_explicitly(
    rendered_default: Path,
) -> None:
    destination = rendered_default
    workflows = destination / ".github" / "workflows"
    callers = {
        "quality": _workflow(workflows / "ci.yml")["jobs"]["quality"],
        "pr-link": _workflow(workflows / "pr-link.yml")["jobs"]["pr-link"],
        "agent-review": _workflow(workflows / "agent-review.yml")["jobs"]["agent-review"],
    }
    for name, job in callers.items():
        reference = job["uses"]
        assert f"reusable-{name}.yml@" in reference
        assert not reference.endswith(("@main", "@master", "@HEAD"))
        assert re.fullmatch(r".+@[0-9a-f]{40}", reference)
    assert callers["agent-review"]["secrets"] == {
        "claude_code_oauth_token": "${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}"
    }
    assert "inherit" not in callers["agent-review"].get("secrets", {})


def test_rendered_review_caller_uses_subscription_only_credentials(
    rendered_default: Path,
) -> None:
    caller = _workflow(rendered_default / ".github" / "workflows" / "agent-review.yml")["jobs"][
        "agent-review"
    ]

    assert caller["secrets"] == {
        "claude_code_oauth_token": "${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}"
    }
    assert "OPENAI_API_KEY" not in str(caller)
    installation = (
        rendered_default / "docs" / "architecture" / "agent-process-installation.md"
    ).read_text(encoding="utf-8")
    assert "Automatic reviews" in installation
    assert "On every push" in installation


def test_non_default_context_answers_render_a_consistent_project(
    tmp_path: Path,
) -> None:
    destination = render(
        tmp_path,
        "--data",
        'required_status_contexts=["quality / quality", "pr-link / pr-link", "agent-review / agent-review"]',
        "--data",
        "agent_review_context=agent-review / agent-review",
    )
    generated_suite_passes(destination)


def test_create_mode_requires_explicit_confirmation_and_no_placeholder_ids(
    tmp_path: Path,
) -> None:
    destination = render(tmp_path, "--data", "github_repository=example-org/example-repo")

    settings = (destination / "scripts" / "project_settings.py").read_text(encoding="utf-8")
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
    assert "--confirm-create" not in (destination / "AGENTS.md").read_text(encoding="utf-8")
    generated_suite_passes(destination)


def test_create_mode_links_fields_and_persists_real_ids(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = render(tmp_path, "--data", "github_repository=example-org/example-repo")
    monkeypatch.syspath_prepend(str(destination / "scripts"))
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
    monkeypatch.setattr(bootstrap, "_checked", lambda command: calls.append(command) or "")

    bootstrap.main(["--confirm-create"])

    settings = (destination / "scripts" / "project_settings.py").read_text(encoding="utf-8")
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

    call_count = len(calls)
    bootstrap.main([])
    assert len(calls) == call_count


def test_create_mode_rolls_back_a_project_when_activation_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    destination = render(tmp_path, "--data", "github_repository=example-org/example-repo")
    bootstrap = bootstrap_module(destination)
    calls: list[list[str]] = []

    def fake_run(command: list[str]) -> dict[str, object]:
        calls.append(command)
        if command[2] == "create":
            return {"number": 7, "id": "project-7"}
        if command[2] == "field-create":
            raise RuntimeError("field creation denied")
        return {}

    monkeypatch.setattr(bootstrap, "_run", fake_run)
    monkeypatch.setattr(bootstrap, "_checked", lambda command: calls.append(command) or "")

    with pytest.raises(SystemExit) as exc:
        bootstrap.main(["--confirm-create"])

    assert exc.value.code == 1
    assert ["gh", "project", "delete", "7", "--owner", "@me"] in calls
    settings = (destination / "scripts" / "project_settings.py").read_text(encoding="utf-8")
    assert 'PROJECT_ID = ""' in settings
    assert "did not activate" in capsys.readouterr().err


@pytest.mark.parametrize("failure", ["field-list", "settings-write"])
def test_create_mode_rolls_back_late_activation_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    destination = render(tmp_path, "--data", "github_repository=example-org/example-repo")
    bootstrap = bootstrap_module(destination)
    calls: list[list[str]] = []
    valid_fields = {
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
            return {"fields": []} if failure == "field-list" else valid_fields
        return {}

    def fail_write(*args: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(bootstrap, "_run", fake_run)
    monkeypatch.setattr(bootstrap, "_checked", lambda command: calls.append(command) or "")
    if failure == "settings-write":
        monkeypatch.setattr(bootstrap, "_write", fail_write)

    with pytest.raises(SystemExit) as exc:
        bootstrap.main(["--confirm-create"])

    assert exc.value.code == 1
    assert ["gh", "project", "delete", "7", "--owner", "@me"] in calls


def test_rendered_runtime_scripts_do_not_refer_to_removed_project_answers(
    rendered_default: Path,
) -> None:
    destination = rendered_default

    for path in (
        destination / "scripts" / "set_issue_priority.py",
        destination / "scripts" / "set_issue_status.py",
        destination / "scripts" / "issue_branch.py",
        destination / "scripts" / "validate_issue_sections.py",
    ):
        text = path.read_text(encoding="utf-8")
        assert "github_project_number" not in text
        assert "GitHub Project 1" not in text
        assert "hardcoded constants" not in text
