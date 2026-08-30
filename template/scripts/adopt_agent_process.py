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
class _Markers:
    managed: tuple[str, str] = ("<!-- agent-process:begin -->", "<!-- agent-process:end -->")


@dataclass(frozen=True)
class PreflightReport:
    collisions: tuple[str, ...]


CONFLICT_MARKERS = _Markers()
_OWNERSHIP_FILE = ".agent-process/ownership.json"
_RESERVED_PREFIXES = (".agent-process/", ".github/workflows/agent-process-")
_PROCESS_EXCLUSIVE_PREFIXES = (".agents/", ".codex/", ".githooks/", "scripts/")
_ALLOWED_PREFIXES = _RESERVED_PREFIXES + _PROCESS_EXCLUSIVE_PREFIXES
_UNRESOLVED_MARKERS = ("<<<<<<<", "=======", ">>>>>>>")


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
    begin, end = CONFLICT_MARKERS.managed
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
        or not relative.startswith(_ALLOWED_PREFIXES)
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
    return path.is_file() and path.read_bytes() != content and relative not in owned_paths


def _payload_from_directory(directory: Path) -> dict[str, bytes]:
    return {
        path.relative_to(directory).as_posix(): path.read_bytes()
        for path in directory.rglob("*")
        if path.is_file()
    }


def stage_payload(directory: Path) -> dict[str, bytes]:
    """Relocate a normal render while retaining declared process-exclusive paths."""
    staged: dict[str, bytes] = {}
    for relative, content in _payload_from_directory(directory).items():
        if relative == ".copier-answers.yml":
            continue
        destination = (
            relative
            if relative.startswith(_ALLOWED_PREFIXES)
            else f".agent-process/payload/{relative}"
        )
        staged[destination] = content
    return staged


def main() -> int:
    """Run an explicit, reviewable adoption operation from a staged payload."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("preflight", "install", "update"))
    parser.add_argument("destination", type=Path)
    parser.add_argument("payload", type=Path, help="directory containing the release payload")
    args = parser.parse_args()
    payload = stage_payload(args.payload)
    try:
        owned_paths = _owned_paths(args.destination) if args.operation == "update" else frozenset()
    except ValueError as exc:
        print(str(exc))
        return 1
    report = preflight(args.destination, payload, owned_paths=owned_paths)
    invalid = sorted(relative for relative in payload if not relative.startswith(_ALLOWED_PREFIXES))
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
