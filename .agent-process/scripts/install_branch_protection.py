#!/usr/bin/env python3
"""Plan or install the minimum classic branch-protection policy.

The default invocation is read-only. ``--confirm-write`` applies only the
operations printed by the dry run and then re-reads GitHub to verify that all
pre-existing consumer-owned policy survived.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import quote

import yaml

if __package__:
    from .check_branch_protection import (
        NOT_REQUIRED,
        REQUIRED_CONTEXTS,
        contexts_from_protection,
        declaration_problems,
        load_workflows,
    )
else:
    from check_branch_protection import (
        NOT_REQUIRED,
        REQUIRED_CONTEXTS,
        contexts_from_protection,
        declaration_problems,
        load_workflows,
    )

_GH_TIMEOUT_S = 30
_REPOSITORY_ENDPOINT = "repos/{owner}/{repo}"
_OWNED_TOP_LEVEL_FIELDS = frozenset({"required_status_checks", "enforce_admins"})


class BranchProtectionError(RuntimeError):
    """A preflight, transport, mutation, or postcondition failure."""


class BranchProtectionClient(Protocol):
    """Narrow GitHub operations owned by the installer."""

    def get_repository(self) -> Mapping[str, Any]: ...

    def get_protection(self, branch: str) -> Mapping[str, Any] | None: ...

    def add_required_contexts(self, branch: str, contexts: Sequence[str]) -> None: ...

    def enable_required_status_checks(self, branch: str, contexts: Sequence[str]) -> None: ...

    def set_strict_status_checks(self, branch: str) -> None: ...

    def set_admin_enforcement(self, branch: str) -> None: ...

    def create_protection(self, branch: str, payload: Mapping[str, Any]) -> None: ...


@dataclass(frozen=True)
class InstallationReport:
    """Planned actions and the observed state of one installer run."""

    branch: str
    actions: tuple[str, ...]
    changed: bool
    protection: Mapping[str, Any] | None


@dataclass(frozen=True)
class _Operation:
    kind: str
    description: str
    contexts: tuple[str, ...] = ()
    payload: Mapping[str, Any] | None = None


class _GhApiFailure(BranchProtectionError):
    def __init__(self, message: str, *, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


def _baseline() -> dict[str, Any]:
    """Full policy used only when the default branch has no protection."""
    return {
        "required_status_checks": {
            "strict": True,
            "checks": [{"context": context} for context in REQUIRED_CONTEXTS],
        },
        "enforce_admins": True,
        "required_pull_request_reviews": None,
        "restrictions": None,
        "allow_force_pushes": False,
        "allow_deletions": False,
    }


def _status_checks(protection: Mapping[str, Any]) -> Mapping[str, Any] | None:
    value = protection.get("required_status_checks")
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise BranchProtectionError("branch protection has malformed required_status_checks")
    checks = value.get("checks")
    strict = value.get("strict")
    if strict is not None and not isinstance(strict, bool):
        raise BranchProtectionError("branch protection has malformed strict-check setting")
    if checks is not None and not isinstance(checks, list):
        raise BranchProtectionError("branch protection has malformed status-check list")
    for check in checks or []:
        if not isinstance(check, Mapping) or not isinstance(check.get("context"), str):
            raise BranchProtectionError("branch protection has malformed status-check record")
    return value


def _admin_enabled(protection: Mapping[str, Any]) -> bool:
    value = protection.get("enforce_admins")
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if not isinstance(value, Mapping) or not isinstance(value.get("enabled"), bool):
        raise BranchProtectionError("branch protection has malformed admin enforcement")
    return bool(value["enabled"])


def _flag_enabled(protection: Mapping[str, Any], field: str) -> bool:
    value = protection.get(field)
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if not isinstance(value, Mapping) or not isinstance(value.get("enabled"), bool):
        raise BranchProtectionError(f"branch protection has malformed {field}")
    return bool(value["enabled"])


def _validated_protection(value: Any) -> Mapping[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise BranchProtectionError("branch protection response is not an object or null")
    _status_checks(value)
    _admin_enabled(value)
    return value


def _plan(protection: Mapping[str, Any] | None) -> tuple[_Operation, ...]:
    if protection is None:
        return (
            _Operation(
                "create",
                "create the documented baseline protection",
                payload=_baseline(),
            ),
        )

    status = _status_checks(protection)
    operations: list[_Operation] = []
    if status is None:
        operations.append(
            _Operation(
                "enable_status_checks",
                "enable strict required status checks with the process contexts",
                contexts=REQUIRED_CONTEXTS,
            )
        )
    else:
        actual = set(contexts_from_protection(protection))
        missing = tuple(context for context in REQUIRED_CONTEXTS if context not in actual)
        if missing:
            operations.append(
                _Operation(
                    "add_contexts",
                    f"add required contexts: {', '.join(missing)}",
                    contexts=missing,
                )
            )
        if status.get("strict") is not True:
            operations.append(_Operation("set_strict", "enable strict up-to-date status checks"))
    if not _admin_enabled(protection):
        operations.append(_Operation("set_admins", "enforce protection for administrators"))
    return tuple(operations)


def _check_pairs(protection: Mapping[str, Any]) -> set[tuple[str, Any]]:
    status = _status_checks(protection)
    if status is None:
        return set()
    return {(str(check["context"]), check.get("app_id")) for check in status.get("checks") or []}


def _unowned_projection(protection: Mapping[str, Any]) -> dict[str, Any]:
    """Fields no operation in this installer is allowed to change."""
    projection = {
        key: value for key, value in protection.items() if key not in _OWNED_TOP_LEVEL_FIELDS
    }
    status = _status_checks(protection)
    if status is not None:
        projection["required_status_checks metadata"] = {
            key: value
            for key, value in status.items()
            if key not in {"strict", "checks", "contexts"}
        }
    admins = protection.get("enforce_admins")
    if isinstance(admins, Mapping):
        projection["enforce_admins metadata"] = {
            key: value for key, value in admins.items() if key != "enabled"
        }
    return projection


def _state_summary(protection: Mapping[str, Any] | None) -> str:
    if protection is None:
        return "protection absent"
    status = _status_checks(protection)
    strict = status is not None and status.get("strict") is True
    contexts = contexts_from_protection(protection)
    return f"strict={strict}, admins={_admin_enabled(protection)}, contexts={list(contexts)!r}"


def _verify_postcondition(
    before: Mapping[str, Any] | None, after: Mapping[str, Any] | None
) -> list[str]:
    problems: list[str] = []
    if after is None:
        return ["branch protection is still absent"]
    status = _status_checks(after)
    if status is None or status.get("strict") is not True:
        problems.append("strict required status checks are not enabled")
    actual = set(contexts_from_protection(after))
    missing = [context for context in REQUIRED_CONTEXTS if context not in actual]
    if missing:
        problems.append(f"required contexts are missing: {', '.join(missing)}")
    if not _admin_enabled(after):
        problems.append("administrator enforcement is not enabled")

    if before is None:
        if _flag_enabled(after, "allow_force_pushes"):
            problems.append("the new baseline allows force pushes")
        if _flag_enabled(after, "allow_deletions"):
            problems.append("the new baseline allows branch deletion")
        return problems

    lost_pairs = _check_pairs(before) - _check_pairs(after)
    if lost_pairs:
        rendered = ", ".join(f"{context!r}/app_id={app_id!r}" for context, app_id in lost_pairs)
        problems.append(f"pre-existing status-check bindings changed or disappeared: {rendered}")
    if _unowned_projection(before) != _unowned_projection(after):
        problems.append("consumer-owned branch-protection policy changed")
    return problems


def _apply(client: BranchProtectionClient, branch: str, operation: _Operation) -> None:
    if operation.kind == "add_contexts":
        client.add_required_contexts(branch, operation.contexts)
    elif operation.kind == "enable_status_checks":
        client.enable_required_status_checks(branch, operation.contexts)
    elif operation.kind == "set_strict":
        client.set_strict_status_checks(branch)
    elif operation.kind == "set_admins":
        client.set_admin_enforcement(branch)
    elif operation.kind == "create":
        assert operation.payload is not None
        client.create_protection(branch, operation.payload)
    else:
        raise BranchProtectionError(f"unknown branch-protection operation: {operation.kind}")


def _validate_workflow_declaration(workflows_dir: Path) -> None:
    try:
        workflows = load_workflows(workflows_dir)
    except (OSError, yaml.YAMLError) as exc:
        raise BranchProtectionError(f"cannot read local workflow declaration: {exc}") from exc
    problems = declaration_problems(workflows, REQUIRED_CONTEXTS, NOT_REQUIRED)
    if problems:
        raise BranchProtectionError("local workflow declaration is invalid: " + "; ".join(problems))


def install_branch_protection(
    client: BranchProtectionClient,
    *,
    confirm_write: bool = False,
    workflows_dir: Path = Path(".github/workflows"),
) -> InstallationReport:
    """Plan or apply the minimum policy without replacing consumer policy."""
    _validate_workflow_declaration(workflows_dir)
    repository = client.get_repository()
    if not isinstance(repository, Mapping):
        raise BranchProtectionError("repository response is not an object")
    branch = repository.get("default_branch")
    if not isinstance(branch, str) or not branch.strip():
        raise BranchProtectionError("repository response has no valid default branch")
    before = _validated_protection(client.get_protection(branch))
    operations = _plan(before)
    actions = tuple(operation.description for operation in operations)
    if not confirm_write or not operations:
        return InstallationReport(branch, actions, False, before)

    completed: list[str] = []
    for operation in operations:
        try:
            _apply(client, branch, operation)
        except BranchProtectionError as exc:
            try:
                observed = _validated_protection(client.get_protection(branch))
                state = _state_summary(observed)
            except BranchProtectionError as read_exc:
                state = f"post-failure read unavailable: {read_exc}"
            progress = ", ".join(completed) or "no operation returned success"
            raise BranchProtectionError(
                "partial branch-protection update; "
                f"completed: {progress}; failed while {operation.description}: {exc}; "
                f"observed: {state}; rerun the same command to converge"
            ) from exc
        completed.append(operation.description)

    try:
        after = _validated_protection(client.get_protection(branch))
    except BranchProtectionError as exc:
        raise BranchProtectionError(
            "partial branch-protection update; "
            f"completed: {', '.join(completed)}; post-write verification failed: {exc}; "
            "rerun the same command to inspect and converge"
        ) from exc
    problems = _verify_postcondition(before, after)
    if problems:
        raise BranchProtectionError(
            "partial branch-protection update failed postcondition: "
            f"{'; '.join(problems)}; observed: {_state_summary(after)}; "
            "rerun the same command after correcting the reported policy drift"
        )
    return InstallationReport(branch, actions, True, after)


class GhBranchProtectionClient:
    """GitHub CLI adapter; policy decisions stay in the pure functions above."""

    @staticmethod
    def _run(command: list[str], *, body: Mapping[str, Any] | None = None) -> str:
        try:
            completed = subprocess.run(
                command,
                input=json.dumps(body) if body is not None else None,
                text=True,
                capture_output=True,
                encoding="utf-8",
                timeout=_GH_TIMEOUT_S,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise BranchProtectionError(f"cannot run {' '.join(command)}: {exc}") from exc
        if completed.stdout is None or completed.stderr is None:
            raise BranchProtectionError(
                f"output capture failed for {' '.join(command)} (rc={completed.returncode}): "
                f"stdout={completed.stdout!r} stderr={completed.stderr!r}"
            )
        if completed.returncode:
            combined = f"{completed.stderr}\n{completed.stdout}".strip()
            status_match = re.search(r"HTTP\s+(\d{3})", combined)
            status = int(status_match.group(1)) if status_match else None
            raise _GhApiFailure(
                f"{' '.join(command)} failed (rc={completed.returncode}): {combined}",
                status=status,
            )
        return completed.stdout

    @classmethod
    def _api(
        cls,
        method: str,
        endpoint: str,
        body: Mapping[str, Any] | None = None,
    ) -> Any:
        command = ["gh", "api", "--method", method, endpoint]
        if body is not None:
            command.extend(["--input", "-"])
        output = cls._run(command, body=body)
        try:
            return json.loads(output)
        except json.JSONDecodeError as exc:
            raise BranchProtectionError(
                f"GitHub returned malformed JSON for {method} {endpoint}: {output[:200]!r}"
            ) from exc

    @staticmethod
    def _protection_endpoint(branch: str) -> str:
        return f"{_REPOSITORY_ENDPOINT}/branches/{quote(branch, safe='')}/protection"

    def get_repository(self) -> Mapping[str, Any]:
        self._run(["gh", "auth", "status"])
        payload = self._api("GET", _REPOSITORY_ENDPOINT)
        if not isinstance(payload, Mapping):
            raise BranchProtectionError("GitHub repository response is not an object")
        return payload

    def get_protection(self, branch: str) -> Mapping[str, Any] | None:
        endpoint = self._protection_endpoint(branch)
        try:
            payload = self._api("GET", endpoint)
        except _GhApiFailure as exc:
            if exc.status == 404 and "not protected" in str(exc).lower():
                return None
            raise
        if not isinstance(payload, Mapping):
            raise BranchProtectionError("GitHub branch-protection response is not an object")
        return payload

    def add_required_contexts(self, branch: str, contexts: Sequence[str]) -> None:
        endpoint = self._protection_endpoint(branch) + "/required_status_checks/contexts"
        self._api("POST", endpoint, {"contexts": list(contexts)})

    def enable_required_status_checks(self, branch: str, contexts: Sequence[str]) -> None:
        endpoint = self._protection_endpoint(branch) + "/required_status_checks"
        self._api(
            "PATCH",
            endpoint,
            {"strict": True, "checks": [{"context": context} for context in contexts]},
        )

    def set_strict_status_checks(self, branch: str) -> None:
        endpoint = self._protection_endpoint(branch) + "/required_status_checks"
        self._api("PATCH", endpoint, {"strict": True})

    def set_admin_enforcement(self, branch: str) -> None:
        endpoint = self._protection_endpoint(branch) + "/enforce_admins"
        self._api("POST", endpoint)

    def create_protection(self, branch: str, payload: Mapping[str, Any]) -> None:
        self._api("PUT", self._protection_endpoint(branch), payload)


def _print_bindings(protection: Mapping[str, Any] | None) -> None:
    if protection is None:
        print("observed required checks: (protection absent)")
        return
    status = _status_checks(protection)
    checks = status.get("checks") if status is not None else []
    if not checks:
        print("observed required checks: (none)")
        return
    rendered = ", ".join(
        f"{check['context']} (app_id={check.get('app_id', 'unbound')})" for check in checks
    )
    print(f"observed required checks: {rendered}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--confirm-write",
        action="store_true",
        help="apply the printed operations and verify the resulting protection",
    )
    options = parser.parse_args(argv)
    try:
        report = install_branch_protection(
            GhBranchProtectionClient(), confirm_write=options.confirm_write
        )
    except BranchProtectionError as exc:
        print(f"error: branch protection was not installed: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"default branch: {report.branch}")
    if not report.actions:
        print("ok: required branch protection is already configured; no writes")
    elif options.confirm_write:
        for action in report.actions:
            print(f"applied: {action}")
        print("ok: branch-protection postcondition verified")
    else:
        print("dry-run: no remote writes; rerun with --confirm-write to apply:")
        for action in report.actions:
            print(f"  - {action}")
    _print_bindings(report.protection)


if __name__ == "__main__":
    main()
