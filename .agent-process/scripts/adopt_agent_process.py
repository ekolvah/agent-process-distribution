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
    _apply(destination, payload)


def update_payload(destination: Path, payload: dict[str, bytes]) -> None:
    """Update a prior reserved install; reject unclaimed new destinations."""
    _apply(destination, payload)


def _fragment_marker_line_indexes(content: str, marker: str) -> list[int]:
    """Indexes of every line that stands alone as `marker`.

    A line that merely *mentions* a marker as a substring (documentation
    about the delimiter syntax, for instance) must never be mistaken for the
    delimiter itself.
    """
    return [index for index, line in enumerate(content.splitlines()) if line == marker]


def _malformed_fragment_markers(content: str) -> bool:
    """Whether standalone marker lines admit one unambiguous, ordered fragment."""
    begins = _fragment_marker_line_indexes(content, _MANAGED_FRAGMENT_BEGIN)
    ends = _fragment_marker_line_indexes(content, _MANAGED_FRAGMENT_END)
    if len(begins) != len(ends) or len(begins) > 1:
        return True
    return bool(begins) and begins[0] > ends[0]


def update_managed_fragment(path: Path, content: str) -> None:
    """Insert or replace one explicit fragment while preserving all other bytes."""
    begin, end = _MANAGED_FRAGMENT_BEGIN, _MANAGED_FRAGMENT_END
    original = path.read_text(encoding="utf-8") if path.exists() else ""
    if _malformed_fragment_markers(original):
        raise ValueError(f"malformed agent-process markers in {path}")
    lines = original.split("\n")
    begin_index = next((index for index, line in enumerate(lines) if line == begin), None)
    fragment = f"{begin}\n{content.rstrip()}\n{end}"
    if begin_index is not None:
        end_index = next(
            index for index in range(begin_index + 1, len(lines)) if lines[index] == end
        )
        updated = "\n".join(lines[:begin_index] + [fragment] + lines[end_index + 1 :])
    else:
        separator = "" if not original or original.endswith("\n") else "\n"
        updated = f"{original}{separator}{fragment}\n"
    _atomic_write(path, updated.encode("utf-8"))


def _is_reserved_relative_path(relative: str) -> bool:
    return (
        not Path(relative).is_absolute()
        and ".." not in Path(relative).parts
        and _is_process_path(relative)
    )


def _validate_payload(payload: dict[str, bytes]) -> None:
    invalid = sorted(relative for relative in payload if not _is_reserved_relative_path(relative))
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
    """Scan only process-managed paths — a product fixture or doc containing
    literal conflict-marker text outside this scope is not a Copier artifact.
    """
    problems = []
    for path in destination.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(destination).as_posix()
        is_rej = relative.endswith(".rej")
        # A reject artifact's scope is the file it rejects, not its own
        # suffixed name: "AGENTS.md.rej" is a reject for "AGENTS.md".
        rejected = relative.removesuffix(".rej") if is_rej else relative
        if not _is_process_path(rejected):
            continue
        if is_rej:
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
    if path.exists() and not path.is_file():
        raise ValueError(f"ownership manifest path is not a file: {path}")
    if not path.is_file():
        return frozenset()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"unreadable ownership manifest: {path}") from exc
    paths = data.get("paths") if isinstance(data, dict) else None
    if (
        not isinstance(paths, list)
        or not all(isinstance(item, str) for item in paths)
        or not all(_is_reserved_relative_path(item) for item in paths)
    ):
        # A path outside the reserved namespace would license `_apply`'s
        # retirement step to delete it (ADR-0018) — reject a manifest that
        # names one instead of trusting a hand-edited or malicious file.
        raise ValueError(f"malformed ownership manifest: {path}")
    return frozenset(paths)


def _apply(destination: Path, payload: dict[str, bytes]) -> None:
    _validate_payload(payload)
    unresolved = _unresolved(destination)
    if unresolved:
        raise ValueError("unresolved Copier conflict artifact(s): " + ", ".join(unresolved))
    owned_paths = _owned_paths(destination)
    report = preflight(destination, payload, owned_paths=owned_paths)
    collisions = report.collisions
    if collisions:
        raise ValueError("payload collides with consumer-owned file(s): " + ", ".join(collisions))
    # ADR-0018: the manifest, not a hand-picked list, licenses removal — a
    # path this release no longer ships and no longer owns is retired, not
    # merely forgotten. Managed-fragment targets are exempt: they are merge
    # targets holding consumer bytes, never a file this process fully owns.
    retired = sorted(owned_paths - payload.keys() - _MANAGED_FRAGMENT_TARGETS)
    symlinked = [
        relative
        for relative in retired
        if _has_symlinked_parent(destination, destination / relative)
    ]
    if symlinked:
        raise ValueError(
            "retired path(s) sit behind a symlinked parent, refusing to delete: "
            + ", ".join(symlinked)
        )
    became_directories = [
        relative
        for relative in retired
        if (destination / relative).is_dir() and not (destination / relative).is_symlink()
    ]
    if became_directories:
        raise ValueError(
            "retired path(s) have become directories, refusing to delete: "
            + ", ".join(became_directories)
        )
    for relative, content in sorted(payload.items()):
        if relative in _MANAGED_FRAGMENT_TARGETS:
            update_managed_fragment(destination / relative, content.decode("utf-8"))
        elif (
            relative in _PRESERVED_ON_UPDATE_TARGETS
            and relative in owned_paths
            and (destination / relative).is_file()
        ):
            # A prior adoption already replaced this placeholder with live,
            # bootstrap-generated state; a re-`install` must not wipe it out
            # any more than an `update` would — ownership, not the `updating`
            # flag, is what proves a prior adoption happened.
            continue
        else:
            _atomic_write(destination / relative, content)
    for relative in retired:
        path = destination / relative
        # A path that is merely a case-only (or otherwise non-canonical)
        # respelling of a payload path just written is not a real removal:
        # on a case-insensitive or case-preserving destination the two
        # spellings name the same filesystem entry. `samefile` asks the
        # filesystem directly instead of guessing from string form — a
        # guess like `os.path.normcase` is a no-op on POSIX and so misses
        # this on the default case-insensitive macOS volume.
        if _retired_path_is_payload_alias(destination, relative, payload):
            continue
        if path.is_file() or path.is_symlink():
            path.unlink()
            print(f"removed retired path: {relative}")
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


def _has_symlinked_parent(destination: Path, path: Path) -> bool:
    """Whether a parent between `path` and `destination` is a symlink (or a
    non-directory), which could resolve `path` outside `destination`.
    """
    parent = path.parent
    while parent != destination:
        if parent.is_symlink() or (parent.exists() and not parent.is_dir()):
            return True
        parent = parent.parent
    return False


def _retired_path_is_payload_alias(
    destination: Path, relative: str, payload: dict[str, bytes]
) -> bool:
    """Whether a retired path is, on disk, the same entry as a payload path
    just written — a case-only rename (or other non-canonical respelling) on
    a case-insensitive or case-preserving destination, not an actual removal.
    """
    path = destination / relative
    if not path.exists():
        return False
    for payload_relative in payload:
        payload_path = destination / payload_relative
        try:
            if payload_path.exists() and payload_path.samefile(path):
                return True
        except OSError:
            continue
    return False


def _path_conflicts(
    destination: Path, relative: str, content: bytes, owned_paths: frozenset[str]
) -> bool:
    """Whether a path or one of its parents prevents an atomic payload write."""
    path = destination / relative
    if path.exists() and not path.is_file():
        return True
    if _has_symlinked_parent(destination, path):
        return True
    if relative in _MANAGED_FRAGMENT_TARGETS:
        if path.is_symlink():
            return True
        if path.is_file():
            try:
                existing = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                return True
            if _malformed_fragment_markers(existing):
                return True
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
    if not args.payload.is_dir():
        print(f"payload directory does not exist: {args.payload}")
        return 1
    payload = _payload_from_directory(args.payload)
    if not payload:
        print(f"payload directory has no files: {args.payload}")
        return 1
    try:
        owned_paths = _owned_paths(args.destination)
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
