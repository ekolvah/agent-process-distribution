"""Render contracts for required GitHub Project bootstrap modes."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]


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
    path = destination / ".agent-process" / "scripts" / "bootstrap_github_project.py"
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
        [sys.executable, "-m", "pytest", "-q", "-c", ".agent-process/pyproject.toml"],
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
    answers = yaml.safe_load(
        (destination / ".agent-process" / "copier-answers.yml").read_text(encoding="utf-8")
    )
    workflows = destination / ".github" / "workflows"
    contexts = tuple(answers["required_status_contexts"])

    assert {
        "ci.yml",
        "pr-link.yml",
        "agent-review.yml",
    } <= {p.name for p in workflows.iterdir()}
    for context, filename in zip(
        contexts,
        ("ci.yml", "pr-link.yml", "agent-review.yml"),
        strict=True,
    ):
        job_key = context.split(" / ", 1)[0]
        job = _workflow(workflows / filename)["jobs"][job_key]
        assert "uses" in job
        if job_key == "quality":
            assert "with" not in job
        assert job_key == context.split(" / ", 1)[0]


def test_rendered_project_ships_the_standalone_review_contract(rendered_default: Path) -> None:
    destination = rendered_default

    assert (destination / ".agent-process" / "REVIEW_CONTRACT.md").is_file()
    assert "[REVIEW_CONTRACT.md](.agent-process/REVIEW_CONTRACT.md)" in (
        destination / "AGENTS.md"
    ).read_text(encoding="utf-8")
    assert not (destination / ".agent-process" / "scripts" / "extract_review_prompt.py").exists()


def test_rendered_callers_reference_main_with_claude_fallback_secret(
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
        assert reference.endswith("@main")
    assert callers["agent-review"]["secrets"] == {
        "claude_code_oauth_token": "${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}"
    }


def test_rendered_review_caller_uses_owner_requested_codex_review(
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
        rendered_default
        / ".agent-process"
        / "docs"
        / "architecture"
        / "agent-process-installation.md"
    ).read_text(encoding="utf-8")
    assert "@codex review" in installation
    assert "enable **Automatic reviews**" not in installation


def test_rendered_implementer_requests_codex_for_every_reviewed_head(
    rendered_default: Path,
) -> None:
    process = (
        rendered_default / ".agent-process" / "docs" / "architecture" / "agent-process.md"
    ).read_text(encoding="utf-8")
    implementer = (
        rendered_default / ".agents" / "skills" / "implement-issue" / "SKILL.md"
    ).read_text(encoding="utf-8")

    request = "python .agent-process/scripts/request_codex_review.py --request <PR>"
    assert request in process
    assert request in implementer
    assert process.index(request) < process.index("gh pr checks <PR> --watch")
    assert implementer.index(request) < implementer.index("gh pr checks <PR> --watch")


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

    settings = (destination / ".agent-process" / "scripts" / "project_settings.py").read_text(
        encoding="utf-8"
    )
    assert "PVT_" not in settings
    assert "REPLACE_ME" not in settings
    bootstrap = destination / ".agent-process" / "scripts" / "bootstrap_github_project.py"
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

    bootstrap = (
        destination / ".agent-process" / "scripts" / "bootstrap_github_project.py"
    ).read_text(encoding="utf-8")
    assert 'MODE = "existing"' in bootstrap
    assert 'OWNER = "example-org"' in bootstrap
    assert 'EXISTING_NUMBER = "42"' in bootstrap
    assert "--confirm-create" not in (destination / "AGENTS.md").read_text(encoding="utf-8")
    generated_suite_passes(destination)


def test_create_mode_links_builtin_status_and_preserves_all_options(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = render(tmp_path, "--data", "github_repository=example-org/example-repo")
    monkeypatch.syspath_prepend(str(destination / ".agent-process" / "scripts"))
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
                "name": "Status",
                "options": [
                    {"id": "status-todo", "name": "Todo"},
                    {"id": "status-progress", "name": "In Progress"},
                    {"id": "status-done", "name": "Done"},
                    {"id": "status-planned", "name": "Planned"},
                ],
            },
        ]
    }

    def fake_run(command: list[str]) -> dict[str, object]:
        calls.append(command)
        if command == ["gh", "api", "user"]:
            return {"login": "octocat"}
        if command[2] == "create":
            return {"number": 7, "id": "project-7"}
        if command[2] == "field-list":
            return fields
        return {}

    monkeypatch.setattr(bootstrap, "_run", fake_run)
    monkeypatch.setattr(bootstrap, "_checked", lambda command: calls.append(command) or "")
    graph_calls: list[dict[str, object]] = []

    def fake_graphql(query: str, variables: dict[str, object]) -> dict[str, object]:
        graph_calls.append(variables)
        if query.startswith("query"):
            return {
                "data": {
                    "node": {
                        "fields": {
                            "nodes": [
                                {
                                    "id": "status-field",
                                    "name": "Status",
                                    "options": [
                                        {
                                            "id": "status-todo",
                                            "name": "Todo",
                                            "color": "GRAY",
                                            "description": "",
                                        },
                                        {
                                            "id": "status-progress",
                                            "name": "In Progress",
                                            "color": "YELLOW",
                                            "description": "",
                                        },
                                        {
                                            "id": "status-done",
                                            "name": "Done",
                                            "color": "GREEN",
                                            "description": "",
                                        },
                                    ],
                                }
                            ]
                        }
                    }
                }
            }
        assert variables["field"] == "status-field"
        assert [option["id"] for option in variables["options"][:-1]] == [
            "status-todo",
            "status-progress",
            "status-done",
        ]
        assert all(
            set(option) == {"id", "name", "color", "description"}
            for option in variables["options"][:-1]
        )
        assert variables["options"][-1]["name"] == "Planned"
        return {"data": {"updateProjectV2Field": {"projectV2Field": {"id": "status-field"}}}}

    monkeypatch.setattr(bootstrap, "_graphql", fake_graphql)

    bootstrap.main(["--confirm-create"])

    settings = (destination / ".agent-process" / "scripts" / "project_settings.py").read_text(
        encoding="utf-8"
    )
    assert 'PROJECT_NUMBER = "7"' in settings
    assert 'PROJECT_OWNER = "octocat"' in settings
    assert 'PROJECT_ID = "project-7"' in settings
    assert "priority-high" in settings
    assert "status-progress" in settings

    settings_path = destination / ".agent-process" / "scripts" / "project_settings.py"
    spec = importlib.util.spec_from_file_location("generated_project_settings", settings_path)
    assert spec is not None and spec.loader is not None
    generated_settings = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generated_settings)
    generated_settings.require_configured()

    for name, value in (
        ("PROJECT_ID", ""),
        ("PRIORITY_OPTION_IDS", {"high": "priority-high"}),
        ("STATUS_OPTION_IDS", {"planned": "status-planned"}),
    ):
        with monkeypatch.context() as corrupted:
            corrupted.setattr(generated_settings, name, value)
            with pytest.raises(RuntimeError, match="bootstrap is incomplete"):
                generated_settings.require_configured()

    assert [
        "gh",
        "project",
        "link",
        "7",
        "--owner",
        "octocat",
        "--repo",
        "example-org/example-repo",
    ] in calls
    assert not any("Agent status" in command for command in calls)
    assert len(graph_calls) == 2


def test_existing_mode_requires_builtin_status_subset(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = render(
        tmp_path,
        "--data",
        "github_project_mode=existing",
        "--data",
        "github_project_owner=example-org",
        "--data",
        "existing_github_project_number=42",
    )
    bootstrap = bootstrap_module(destination)
    fields = {
        "fields": [
            {
                "id": "priority",
                "name": "Priority",
                "options": [
                    {"id": "high", "name": "High"},
                    {"id": "medium", "name": "Medium"},
                    {"id": "low", "name": "Low"},
                ],
            },
            {
                "id": "status",
                "name": "Status",
                "options": [
                    {"id": "todo", "name": "Todo"},
                    {"id": "planned", "name": "pLaNnEd"},
                    {"id": "progress", "name": "IN PROGRESS"},
                    {"id": "done", "name": "Done"},
                ],
            },
        ]
    }

    def fake_run(command: list[str]) -> dict[str, object]:
        if command[2] == "view":
            return {"id": "project-42"}
        if command[2] == "field-list":
            return fields
        raise AssertionError(f"unexpected mutation: {command}")

    monkeypatch.setattr(bootstrap, "_run", fake_run)
    bootstrap.main([])

    settings = (destination / ".agent-process" / "scripts" / "project_settings.py").read_text(
        encoding="utf-8"
    )
    assert 'STATUS_FIELD_ID = "status"' in settings
    assert 'STATUS_OPTION_IDS = {"planned": "planned", "in-progress": "progress"}' in settings


def test_existing_mode_confirmed_status_setup_re_reads_before_writing_settings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = render(
        tmp_path,
        "--data",
        "github_project_mode=existing",
        "--data",
        "github_project_owner=example-org",
        "--data",
        "existing_github_project_number=42",
    )
    bootstrap = bootstrap_module(destination)
    remote_updated = False
    events: list[str] = []

    priority = {
        "id": "priority",
        "name": "Priority",
        "options": [
            {"id": "high", "name": "High"},
            {"id": "medium", "name": "Medium"},
            {"id": "low", "name": "Low"},
        ],
    }
    status = {
        "id": "status",
        "name": "Status",
        "options": [
            {"id": "todo", "name": "Todo"},
            {"id": "progress", "name": "In Progress"},
            {"id": "done", "name": "Done"},
        ],
    }

    def fake_run(command: list[str]) -> dict[str, object]:
        events.append("field-list" if command[2] == "field-list" else command[2])
        if command[2] == "view":
            return {"id": "project-42"}
        if command[2] == "field-list":
            reread_status = {**status, "options": [*status["options"]]}
            if remote_updated:
                reread_status["options"].append({"id": "planned", "name": "Planned"})
            return {"fields": [priority, reread_status]}
        raise AssertionError(f"unexpected command: {command}")

    def fake_graphql(query: str, variables: dict[str, object]) -> dict[str, object]:
        nonlocal remote_updated
        if query.startswith("query"):
            return {
                "data": {
                    "node": {
                        "fields": {
                            "nodes": [
                                {
                                    **status,
                                    "options": [
                                        {
                                            **option,
                                            "color": "GRAY",
                                            "description": "",
                                        }
                                        for option in status["options"]
                                    ],
                                }
                            ]
                        }
                    }
                }
            }
        assert variables["field"] == "status"
        assert [option["id"] for option in variables["options"][:-1]] == [
            "todo",
            "progress",
            "done",
        ]
        assert all(
            set(option) == {"id", "name", "color", "description"}
            for option in variables["options"][:-1]
        )
        assert variables["options"][-1]["name"] == "Planned"
        remote_updated = True
        events.append("update-status")
        return {"data": {"updateProjectV2Field": {"projectV2Field": {"id": "status"}}}}

    monkeypatch.setattr(bootstrap, "_run", fake_run)
    monkeypatch.setattr(bootstrap, "_graphql", fake_graphql)

    bootstrap.main(["--confirm-status-setup"])

    settings = (destination / ".agent-process" / "scripts" / "project_settings.py").read_text(
        encoding="utf-8"
    )
    assert 'STATUS_FIELD_ID = "status"' in settings
    assert '"planned": "planned"' in settings
    assert events == ["view", "field-list", "update-status", "field-list"]


def test_confirmed_status_setup_targets_an_activated_create_project(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = render(tmp_path, "--data", "github_repository=example-org/example-repo")
    bootstrap = bootstrap_module(destination)
    writes: list[tuple[str, str, str]] = []
    field_reads: list[tuple[str, str]] = []

    monkeypatch.setattr(
        bootstrap,
        "_configured_project",
        lambda: ("7", "project-7", "octocat"),
        raising=False,
    )
    monkeypatch.setattr(
        bootstrap,
        "_ensure_builtin_planned",
        lambda project_id: writes.append(("ensure", project_id, "")),
    )
    monkeypatch.setattr(
        bootstrap,
        "_fields",
        lambda number, owner: (
            field_reads.append((number, owner))
            or [
                {
                    "id": "priority",
                    "name": "Priority",
                    "options": [
                        {"id": "high", "name": "High"},
                        {"id": "medium", "name": "Medium"},
                        {"id": "low", "name": "Low"},
                    ],
                }
            ]
        ),
    )
    monkeypatch.setattr(
        bootstrap,
        "_write",
        lambda number, project_id, fields, owner: writes.append((number, project_id, owner)),
    )

    bootstrap.main(["--confirm-status-setup"])

    assert writes == [("ensure", "project-7", ""), ("7", "project-7", "octocat")]
    assert field_reads == [("7", "octocat"), ("7", "octocat")]


@pytest.mark.parametrize("owner_type", ["User", "Organization"])
def test_configured_project_resolves_persisted_at_me_from_project_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, owner_type: str
) -> None:
    destination = render(tmp_path, "--data", "github_repository=example-org/example-repo")
    bootstrap = bootstrap_module(destination)
    settings = ModuleType("project_settings")
    settings.PROJECT_NUMBER = "7"
    settings.PROJECT_ID = "project-7"
    settings.PROJECT_OWNER = "@me"
    settings.require_configured = lambda: None
    monkeypatch.setitem(sys.modules, "project_settings", settings)
    monkeypatch.setattr(bootstrap.importlib, "reload", lambda module: module)
    monkeypatch.setattr(
        bootstrap,
        "_run",
        lambda command: pytest.fail(
            f"configured owner must not depend on current viewer: {command}"
        ),
    )

    def project_identity(query: str, variables: dict[str, object]) -> dict[str, object]:
        assert variables == {"project": "project-7"}
        assert "... on User" in query
        assert "... on Organization" in query
        return {
            "data": {
                "node": {
                    "__typename": "ProjectV2",
                    "id": "project-7",
                    "number": 7,
                    "owner": {"__typename": owner_type, "login": "owner-a"},
                }
            }
        }

    monkeypatch.setattr(bootstrap, "_graphql", project_identity)

    assert bootstrap._configured_project() == ("7", "project-7", "owner-a")


def test_configured_project_rejects_number_mismatch_before_field_reads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = render(tmp_path, "--data", "github_repository=example-org/example-repo")
    bootstrap = bootstrap_module(destination)
    settings = ModuleType("project_settings")
    settings.PROJECT_NUMBER = "7"
    settings.PROJECT_ID = "project-8"
    settings.PROJECT_OWNER = "@me"
    settings.require_configured = lambda: None
    monkeypatch.setitem(sys.modules, "project_settings", settings)
    monkeypatch.setattr(bootstrap.importlib, "reload", lambda module: module)
    monkeypatch.setattr(
        bootstrap,
        "_run",
        lambda command: pytest.fail(f"mismatched identity must fail before field reads: {command}"),
    )
    monkeypatch.setattr(
        bootstrap,
        "_graphql",
        lambda query, variables: {
            "data": {
                "node": {
                    "__typename": "ProjectV2",
                    "id": "project-8",
                    "number": 8,
                    "owner": {"__typename": "User", "login": "owner-a"},
                }
            }
        },
    )

    with pytest.raises(RuntimeError, match="number 8.*configured number 7"):
        bootstrap._configured_project()


def test_existing_mode_preflight_failure_keeps_settings_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    destination = render(
        tmp_path,
        "--data",
        "github_project_mode=existing",
        "--data",
        "github_project_owner=example-org",
        "--data",
        "existing_github_project_number=42",
    )
    bootstrap = bootstrap_module(destination)
    mutations: list[dict[str, object]] = []

    monkeypatch.setattr(
        bootstrap,
        "_run",
        lambda command: (
            {"id": "project-42"}
            if command[2] == "view"
            else {
                "fields": [
                    {
                        "id": "priority",
                        "name": "Priority",
                        "options": [
                            {"id": "high", "name": "High"},
                            {"id": "medium", "name": "Medium"},
                            {"id": "low", "name": "Low"},
                        ],
                    }
                ]
            }
        ),
    )

    def incomplete_status(query: str, variables: dict[str, object]) -> dict[str, object]:
        if not query.startswith("query"):
            mutations.append(variables)
        return {
            "data": {
                "node": {
                    "fields": {
                        "nodes": [
                            {
                                "id": "status",
                                "name": "Status",
                                "options": [
                                    {
                                        "id": "todo",
                                        "name": "Todo",
                                        "color": "GRAY",
                                        "description": "",
                                    },
                                    {
                                        "id": "done",
                                        "name": "Done",
                                        "color": "GREEN",
                                        "description": "",
                                    },
                                ],
                            }
                        ]
                    }
                }
            }
        }

    monkeypatch.setattr(bootstrap, "_graphql", incomplete_status)

    with pytest.raises(SystemExit) as exc:
        bootstrap.main(["--confirm-status-setup"])

    assert exc.value.code == 1
    assert mutations == []
    assert 'PROJECT_ID = ""' in (
        destination / ".agent-process" / "scripts" / "project_settings.py"
    ).read_text(encoding="utf-8")
    assert "In Progress" in capsys.readouterr().err


def test_existing_mode_rejects_drifted_priority_before_status_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    destination = render(
        tmp_path,
        "--data",
        "github_project_mode=existing",
        "--data",
        "github_project_owner=example-org",
        "--data",
        "existing_github_project_number=42",
    )
    bootstrap = bootstrap_module(destination)
    mutations: list[dict[str, object]] = []

    monkeypatch.setattr(
        bootstrap,
        "_run",
        lambda command: (
            {"id": "project-42"}
            if command[2] == "view"
            else {
                "fields": [
                    {
                        "id": "priority",
                        "name": "Priority",
                        "options": [
                            {"id": "high", "name": "High"},
                            {"id": "medium", "name": "Medium"},
                        ],
                    }
                ]
            }
        ),
    )
    monkeypatch.setattr(
        bootstrap,
        "_graphql",
        lambda query, variables: mutations.append(variables) or {},
    )

    with pytest.raises(SystemExit) as exc:
        bootstrap.main(["--confirm-status-setup"])

    assert exc.value.code == 1
    assert mutations == []
    assert "Priority" in capsys.readouterr().err


def test_rendered_project_does_not_ship_project_status_migrator(rendered_default: Path) -> None:
    assert not (
        rendered_default / ".agent-process" / "scripts" / "migrate_project_status.py"
    ).exists()


def test_create_mode_with_literal_owner_skips_resolution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = render(
        tmp_path,
        "--data",
        "github_repository=example-org/example-repo",
        "--data",
        "github_project_owner=example-org",
    )
    bootstrap = bootstrap_module(destination)
    calls: list[list[str]] = []

    def fake_run(command: list[str]) -> dict[str, object]:
        calls.append(command)
        if command[2] == "create":
            return {"number": 7, "id": "project-7"}
        if command[2] == "field-list":
            return {"fields": []}
        return {}

    monkeypatch.setattr(bootstrap, "_run", fake_run)
    monkeypatch.setattr(bootstrap, "_checked", lambda command: calls.append(command) or "")

    with pytest.raises(SystemExit):
        bootstrap.main(["--confirm-create"])

    assert ["gh", "api", "user"] not in calls
    assert [
        "gh",
        "project",
        "link",
        "7",
        "--owner",
        "example-org",
        "--repo",
        "example-org/example-repo",
    ] in calls


def test_create_mode_fails_before_create_when_owner_unresolvable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    destination = render(tmp_path, "--data", "github_repository=example-org/example-repo")
    bootstrap = bootstrap_module(destination)
    calls: list[list[str]] = []

    def fake_run(command: list[str]) -> dict[str, object]:
        calls.append(command)
        if command == ["gh", "api", "user"]:
            return {"login": ""}
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr(bootstrap, "_run", fake_run)
    monkeypatch.setattr(bootstrap, "_checked", lambda command: calls.append(command) or "")

    with pytest.raises(SystemExit) as exc:
        bootstrap.main(["--confirm-create"])

    assert exc.value.code == 1
    assert ["gh", "project", "create"] not in calls
    assert "cannot resolve the authenticated login" in capsys.readouterr().err


def test_create_mode_rolls_back_a_project_when_activation_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    destination = render(tmp_path, "--data", "github_repository=example-org/example-repo")
    bootstrap = bootstrap_module(destination)
    calls: list[list[str]] = []

    def fake_run(command: list[str]) -> dict[str, object]:
        calls.append(command)
        if command == ["gh", "api", "user"]:
            return {"login": "octocat"}
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
    settings = (destination / ".agent-process" / "scripts" / "project_settings.py").read_text(
        encoding="utf-8"
    )
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
        if command == ["gh", "api", "user"]:
            return {"login": "octocat"}
        if command[2] == "create":
            return {"number": 7, "id": "project-7"}
        if command[2] == "field-list":
            return {"fields": []} if failure == "field-list" else valid_fields
        return {}

    def fail_write(*args: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(bootstrap, "_run", fake_run)
    monkeypatch.setattr(bootstrap, "_checked", lambda command: calls.append(command) or "")
    monkeypatch.setattr(
        bootstrap,
        "_graphql",
        lambda query, variables: {
            "data": {
                "node": {
                    "fields": {
                        "nodes": [
                            {
                                "id": "status-field",
                                "name": "Status",
                                "options": [
                                    {
                                        "id": "todo",
                                        "name": "Todo",
                                        "color": "GRAY",
                                        "description": "",
                                    },
                                    {
                                        "id": "progress",
                                        "name": "In Progress",
                                        "color": "YELLOW",
                                        "description": "",
                                    },
                                    {
                                        "id": "done",
                                        "name": "Done",
                                        "color": "GREEN",
                                        "description": "",
                                    },
                                ],
                            }
                        ]
                    }
                }
            }
        },
    )
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
        destination / ".agent-process" / "scripts" / "set_issue_priority.py",
        destination / ".agent-process" / "scripts" / "set_issue_status.py",
        destination / ".agent-process" / "scripts" / "issue_branch.py",
        destination / ".agent-process" / "scripts" / "validate_issue_sections.py",
    ):
        text = path.read_text(encoding="utf-8")
        assert "github_project_number" not in text
        assert "GitHub Project 1" not in text
        assert "hardcoded constants" not in text
