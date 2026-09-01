#!/usr/bin/env python3
"""Adopt reserved agent-process files without replacing consumer configuration."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PreflightReport:
    collisions: tuple[str, ...]


_MANAGED_FRAGMENT_BEGIN = "<!-- agent-process:begin -->"
_MANAGED_FRAGMENT_END = "<!-- agent-process:end -->"
_OWNERSHIP_FILE = ".agent-process/ownership.json"
_PROCESS_ROOT = ".agent-process/"
_CLOSED_ROOT_FILES = frozenset(
    {
        ".github/workflows/ci.yml",
        ".github/workflows/agent-review.yml",
        ".github/workflows/pr-link.yml",
        ".github/pull_request_template.md",
        "AGENTS.md",
        ".gitignore",
    }
)
_CLOSED_ROOT_PREFIXES = (".agents/", ".claude/", ".codex/", "tests/agent_process/")
_UNRESOLVED_MARKERS = ("<<<<<<<", "=======", ">>>>>>>")
# ADR-0019: a consumer's own content coexists with the process's delimited
# fragment in the same file, so these two never collide on differing bytes —
# they merge instead.
_MANAGED_FRAGMENT_TARGETS = frozenset({"AGENTS.md", ".gitignore"})
# bootstrap_github_project.py rewrites this placeholder in place with the
# repository's generated Project number and field IDs; an update must not
# replace that live state with the release's empty template again.
_PRESERVED_ON_UPDATE_TARGETS = frozenset({".agent-process/scripts/project_settings.py"})


def _is_process_path(relative: str) -> bool:
    return (
        relative.startswith(_PROCESS_ROOT)
        or relative in _CLOSED_ROOT_FILES
        or relative.startswith(_CLOSED_ROOT_PREFIXES)
    )


def preflight(
    destination: Path, payload: dict[str, bytes], *, owned_paths: frozenset[str] = frozenset()
) -> PreflightReport:
    """Inventory every foreign payload path without changing ``destination``."""
    collisions = tuple(
        relative
        for relative, content in sorted(payload.items())
        if _path_conflicts(destination, relative, content, owned_paths)
    )
    return PreflightReport(collisions)


def install_payload(destination: Path, payload: dict[str, bytes]) -> None:
    """Install only collision-resistant files after a complete preflight."""
    _apply(destination, payload, updating=False)


def update_payload(destination: Path, payload: dict[str, bytes]) -> None:
    """Update a prior reserved install; reject unclaimed new destinations."""
    _apply(destination, payload, updating=True)


def update_managed_fragment(path: Path, content: str) -> None:
    """Insert or replace one explicit fragment while preserving all other bytes."""
    begin, end = _MANAGED_FRAGMENT_BEGIN, _MANAGED_FRAGMENT_END
    original = path.read_text(encoding="utf-8") if path.exists() else ""
    begin_count = original.count(begin)
    end_count = original.count(end)
    if begin_count != end_count or begin_count > 1:
        raise ValueError(f"malformed agent-process markers in {path}")
    fragment = f"{begin}\n{content.rstrip()}\n{end}"
    if begin_count:
        start = original.index(begin)
        finish = original.index(end, start) + len(end)
        updated = original[:start] + fragment + original[finish:]
    else:
        separator = "" if not original or original.endswith("\n") else "\n"
        updated = f"{original}{separator}{fragment}\n"
    _atomic_write(path, updated.encode("utf-8"))


def _validate_payload(payload: dict[str, bytes]) -> None:
    invalid = sorted(
        relative
        for relative in payload
        if Path(relative).is_absolute()
        or ".." in Path(relative).parts
        or not _is_process_path(relative)
    )
    if invalid:
        raise ValueError("payload has non-reserved destination(s): " + ", ".join(invalid))


def _has_conflict_block(content: str) -> bool:
    """Whether ``content`` contains a coherent opener/separator/closer conflict block."""
    opener, separator, closer = _UNRESOLVED_MARKERS
    stage = 0
    for line in content.splitlines():
        if line.startswith(opener):
            stage = 1
        elif stage == 1 and line.startswith(separator):
            stage = 2
        elif stage == 2 and line.startswith(closer):
            return True
    return False


def _unresolved(destination: Path) -> tuple[str, ...]:
    problems = []
    for path in destination.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(destination).as_posix()
        if relative.endswith(".rej"):
            problems.append(relative)
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if _has_conflict_block(content):
            problems.append(relative)
    return tuple(sorted(problems))


def _owned_paths(destination: Path) -> frozenset[str]:
    path = destination / _OWNERSHIP_FILE
    if not path.is_file():
        return frozenset()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"unreadable ownership manifest: {path}") from exc
    paths = data.get("paths") if isinstance(data, dict) else None
    if not isinstance(paths, list) or not all(isinstance(item, str) for item in paths):
        raise ValueError(f"malformed ownership manifest: {path}")
    return frozenset(paths)


def _apply(destination: Path, payload: dict[str, bytes], *, updating: bool) -> None:
    _validate_payload(payload)
    unresolved = _unresolved(destination)
    if unresolved:
        raise ValueError("unresolved Copier conflict artifact(s): " + ", ".join(unresolved))
    owned_paths = _owned_paths(destination) if updating else frozenset()
    report = preflight(destination, payload, owned_paths=owned_paths)
    collisions = report.collisions
    if collisions:
        raise ValueError("payload collides with consumer-owned file(s): " + ", ".join(collisions))
    for relative, content in sorted(payload.items()):
        if relative in _MANAGED_FRAGMENT_TARGETS:
            update_managed_fragment(destination / relative, content.decode("utf-8"))
        elif (
            updating
            and relative in _PRESERVED_ON_UPDATE_TARGETS
            and (destination / relative).is_file()
        ):
            continue
        else:
            _atomic_write(destination / relative, content)
    manifest = json.dumps({"paths": sorted(payload)}, indent=2) + "\n"
    _atomic_write(destination / _OWNERSHIP_FILE, manifest.encode("utf-8"))


def _atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
        handle.write(content)
        temporary = Path(handle.name)
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _path_conflicts(
    destination: Path, relative: str, content: bytes, owned_paths: frozenset[str]
) -> bool:
    """Whether a path or one of its parents prevents an atomic payload write."""
    path = destination / relative
    if path.exists() and not path.is_file():
        return True
    parent = path.parent
    while parent != destination:
        if parent.is_symlink() or (parent.exists() and not parent.is_dir()):
            return True
        parent = parent.parent
    if relative in _MANAGED_FRAGMENT_TARGETS:
        return False
    return path.is_file() and path.read_bytes() != content and relative not in owned_paths


def _payload_from_directory(directory: Path) -> dict[str, bytes]:
    return {
        path.relative_to(directory).as_posix(): path.read_bytes()
        for path in directory.rglob("*")
        if path.is_file()
    }


def main() -> int:
    """Run an explicit, reviewable adoption operation from a staged payload."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("preflight", "install", "update"))
    parser.add_argument("destination", type=Path)
    parser.add_argument("payload", type=Path, help="directory containing the release payload")
    args = parser.parse_args()
    payload = _payload_from_directory(args.payload)
    try:
        owned_paths = _owned_paths(args.destination) if args.operation == "update" else frozenset()
    except ValueError as exc:
        print(str(exc))
        return 1
    report = preflight(args.destination, payload, owned_paths=owned_paths)
    invalid = sorted(relative for relative in payload if not _is_process_path(relative))
    unresolved = _unresolved(args.destination)
    if invalid or report.collisions or unresolved:
        print("adoption preflight rejected; destination was not changed:")
        for label, paths in (
            ("non-reserved payload", invalid),
            ("collisions", report.collisions),
            ("unresolved", unresolved),
        ):
            for relative in paths:
                print(f"  {label}: {relative}")
        return 1
    if args.operation == "install":
        install_payload(args.destination, payload)
    elif args.operation == "update":
        update_payload(args.destination, payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
