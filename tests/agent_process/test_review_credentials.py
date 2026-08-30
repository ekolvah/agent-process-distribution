"""Behavioural contract for the read-only review-credential preflight."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from scripts import check_review_credentials as credentials
from scripts import gh_io

_REPOSITORY = "example-org/example-repo"
_SECRET_ENDPOINT = f"repos/{_REPOSITORY}/actions/secrets?per_page=100"
_ORG_SECRET_ENDPOINT = f"repos/{_REPOSITORY}/actions/organization-secrets?per_page=100"
_INSTALLATIONS_ENDPOINT = "user/installations?per_page=100"


def _page(**collection: object) -> str:
    return json.dumps([collection])


def _install_gh(
    monkeypatch: pytest.MonkeyPatch,
    payloads: dict[str, str],
    *,
    failures: dict[str, str] | None = None,
) -> list[list[str]]:
    calls: list[list[str]] = []
    failed = failures or {}

    def run(args: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        endpoint = args[2]
        if endpoint in failed:
            return subprocess.CompletedProcess(args, 1, "", failed[endpoint])
        return subprocess.CompletedProcess(args, 0, payloads[endpoint], "")

    monkeypatch.setattr(gh_io.subprocess, "run", run)
    return calls


def _all_present_payloads() -> dict[str, str]:
    return {
        _SECRET_ENDPOINT: _page(secrets=[{"name": credentials.REVIEW_SECRET}]),
        _ORG_SECRET_ENDPOINT: _page(secrets=[]),
        _INSTALLATIONS_ENDPOINT: _page(
            installations=[{"id": 42, "app_slug": credentials.codex_app_slug()}]
        ),
        "user/installations/42/repositories?per_page=100": _page(
            repositories=[{"full_name": _REPOSITORY}]
        ),
    }


def _run() -> None:
    credentials.main(["--repo", _REPOSITORY])


def test_missing_secret_is_named_with_its_fix(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payloads = _all_present_payloads()
    payloads[_SECRET_ENDPOINT] = _page(secrets=[])
    _install_gh(monkeypatch, payloads)

    with pytest.raises(SystemExit, match="1"):
        _run()

    output = capsys.readouterr().err
    assert credentials.REVIEW_SECRET in output
    assert f"gh secret set {credentials.REVIEW_SECRET}" in output


def test_org_inherited_secret_counts_as_present(monkeypatch: pytest.MonkeyPatch) -> None:
    payloads = _all_present_payloads()
    payloads[_SECRET_ENDPOINT] = _page(secrets=[])
    payloads[_ORG_SECRET_ENDPOINT] = _page(secrets=[{"name": credentials.REVIEW_SECRET}])
    _install_gh(monkeypatch, payloads)

    _run()


def test_secret_name_comparison_is_case_insensitive(monkeypatch: pytest.MonkeyPatch) -> None:
    payloads = _all_present_payloads()
    payloads[_SECRET_ENDPOINT] = _page(secrets=[{"name": credentials.REVIEW_SECRET.lower()}])
    _install_gh(monkeypatch, payloads)

    _run()


def test_direct_secret_does_not_require_an_inherited_secret_query(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_gh(
        monkeypatch,
        _all_present_payloads(),
        failures={
            _ORG_SECRET_ENDPOINT: "HTTP 422: inherited list unavailable"  # pragma: allowlist secret
        },
    )

    _run()


def test_installation_excluding_this_repository_is_a_negative(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payloads = _all_present_payloads()
    payloads["user/installations/42/repositories?per_page=100"] = _page(
        repositories=[{"full_name": "example-org/another-repository"}]
    )
    _install_gh(monkeypatch, payloads)

    with pytest.raises(SystemExit, match="1"):
        _run()

    assert "does not cover" in capsys.readouterr().err


def test_gh_failure_exits_two_with_the_real_cause(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _install_gh(
        monkeypatch,
        _all_present_payloads(),
        failures={_INSTALLATIONS_ENDPOINT: "HTTP 403: application token required"},
    )

    with pytest.raises(SystemExit, match="2"):
        _run()

    assert "HTTP 403: application token required" in capsys.readouterr().err


def test_insufficient_permissions_is_not_a_missing_credential(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _install_gh(
        monkeypatch,
        _all_present_payloads(),
        failures={_SECRET_ENDPOINT: "HTTP 404: resource not found"},  # pragma: allowlist secret
    )

    with pytest.raises(SystemExit, match="2"):
        _run()

    output = capsys.readouterr().err
    assert "cannot determine" in output
    assert "missing" not in output


def test_no_secret_value_route_is_requested(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _install_gh(monkeypatch, _all_present_payloads())

    _run()

    endpoints = [call[2] for call in calls]
    assert all("/actions/secrets/" not in endpoint for endpoint in endpoints)
    assert _SECRET_ENDPOINT in endpoints


def test_both_prerequisites_present_exits_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_gh(monkeypatch, _all_present_payloads())

    _run()


def test_documented_script_command_imports_from_a_checkout() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/check_review_credentials.py", "--help"],
        cwd=Path(__file__).resolve().parents[2],
        text=True,
        capture_output=True,
        encoding="utf-8",
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert "--repo" in completed.stdout


def _assert_workflow_uses_the_preflight_secret(workflows: Path) -> None:
    assert list(workflows.glob("agent-process-review.y*ml")), "no rendered review caller matched"
    references = credentials.workflow_secret_references(workflows)
    assert references, "rendered review caller has no explicit secrets. reference"
    assert {name.casefold() for name in references} == {credentials.REVIEW_SECRET.casefold()}


def test_workflow_and_script_name_the_same_secret() -> None:
    _assert_workflow_uses_the_preflight_secret(
        Path(__file__).resolve().parents[2] / ".github" / "workflows"
    )


def test_inherited_secrets_mapping_is_red(tmp_path: Path) -> None:
    workflow = tmp_path / "agent-process-review.yml"
    workflow.write_text("jobs:\n  agent-review:\n    secrets: inherit\n", encoding="utf-8")

    with pytest.raises(AssertionError, match="no explicit secrets"):
        _assert_workflow_uses_the_preflight_secret(tmp_path)
