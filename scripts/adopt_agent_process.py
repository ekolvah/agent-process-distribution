#!/usr/bin/env python3
"""Adopt reserved agent-process files without replacing consumer configuration."""

from __future__ import annotations

import argparse
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
_OWNERSHIP_FILE = ".agent-process/ownership.yml"
_RESERVED_PREFIXES = (".agent-process/", ".github/workflows/agent-process-")
_UNRESOLVED_MARKERS = ("<<<<<<<", "=======", ">>>>>>>")


def preflight(destination: Path, payload: dict[str, bytes]) -> PreflightReport:
    """Inventory every foreign payload path without changing ``destination``."""
    collisions = tuple(
        relative
        for relative, content in sorted(payload.items())
        if (existing := destination / relative).is_file() and existing.read_bytes() != content
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
        or not relative.startswith(_RESERVED_PREFIXES)
    )
    if invalid:
        raise ValueError("payload has non-reserved destination(s): " + ", ".join(invalid))


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
        if any(marker in content for marker in _UNRESOLVED_MARKERS):
            problems.append(relative)
    return tuple(sorted(problems))


def _is_prior_install(destination: Path) -> bool:
    return (destination / _OWNERSHIP_FILE).is_file()


def _apply(destination: Path, payload: dict[str, bytes], *, updating: bool) -> None:
    _validate_payload(payload)
    unresolved = _unresolved(destination)
    if unresolved:
        raise ValueError("unresolved Copier conflict artifact(s): " + ", ".join(unresolved))
    report = preflight(destination, payload)
    collisions = report.collisions
    if updating and _is_prior_install(destination):
        collisions = tuple(
            relative for relative in collisions if not relative.startswith(_RESERVED_PREFIXES)
        )
    if collisions:
        raise ValueError("payload collides with consumer-owned file(s): " + ", ".join(collisions))
    for relative, content in sorted(payload.items()):
        _atomic_write(destination / relative, content)


def _atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
        handle.write(content)
        temporary = Path(handle.name)
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


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
    report = preflight(args.destination, payload)
    invalid = sorted(
        relative for relative in payload if not relative.startswith(_RESERVED_PREFIXES)
    )
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
