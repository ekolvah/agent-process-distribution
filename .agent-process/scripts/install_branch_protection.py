#!/usr/bin/env python3
"""Install the repository's minimum classic branch-protection policy."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


class BranchProtectionError(RuntimeError):
    """A preflight, transport, mutation, or postcondition failure."""


class BranchProtectionClient(Protocol):
    """Narrow GitHub operations owned by the installer."""

    def get_repository(self) -> Mapping[str, Any]: ...

    def get_protection(self, branch: str) -> Mapping[str, Any] | None: ...

    def add_required_contexts(self, branch: str, contexts: Sequence[str]) -> None: ...

    def set_strict_status_checks(self, branch: str) -> None: ...

    def set_admin_enforcement(self, branch: str) -> None: ...

    def create_protection(self, branch: str, payload: Mapping[str, Any]) -> None: ...


@dataclass(frozen=True)
class InstallationReport:
    """Planned actions and the verified state of one installer run."""

    branch: str
    actions: tuple[str, ...]
    changed: bool
    protection: Mapping[str, Any] | None


def install_branch_protection(
    client: BranchProtectionClient,
    *,
    confirm_write: bool = False,
    workflows_dir: Path = Path(".github/workflows"),
) -> InstallationReport:
    """Plan or apply the minimum policy. Implementation follows the RED commit."""
    raise NotImplementedError
