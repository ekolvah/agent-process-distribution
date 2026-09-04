"""Preflight whether Codex CLI trusts this project before its hooks load at all.

Codex loads a project's `.codex/` layer — `hooks.json` included — only for a
directory the operator has recorded as trusted in their own
`~/.codex/config.toml`, under `[projects."<absolute-repo-path>"]` with
`trust_level = "trusted"`. An untrusted checkout silently skips every project
hook, including the `Stop` turn-boundary gate (ADR 0021): an adopter can
follow every documented step and still never have it run. This check is
read-only and makes that otherwise-invisible prerequisite an explicit,
scriptable preflight instead of an assumption.

Exit 0 means the current repository is trusted. Exit 1 means it is not (no
matching entry, or one present but not `trusted`). Exit 2 means the git root
or `~/.codex/config.toml` could not be resolved or parsed.
"""

from __future__ import annotations

import subprocess
import sys
import tomllib
from pathlib import Path

_CONFIG_PATH = Path.home() / ".codex" / "config.toml"


def repo_root() -> Path | None:
    """Resolve the current repository's top-level directory, or `None` off-repo."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
    except OSError:
        return None
    if result.returncode != 0 or not result.stdout.strip():
        return None
    return Path(result.stdout.strip()).resolve()


def is_trusted(config: dict[str, object], root: Path) -> bool:
    """Whether `config`'s `[projects.*]` table trusts `root`."""
    projects = config.get("projects")
    if not isinstance(projects, dict):
        return False
    for raw_path, entry in projects.items():
        if not isinstance(entry, dict) or entry.get("trust_level") != "trusted":
            continue
        try:
            if Path(raw_path).resolve() == root:
                return True
        except OSError:
            continue
    return False


def _remediation(root: Path) -> str:
    return (
        "Run `codex` once inside this repository and accept its folder-trust "
        f'prompt, or add [projects."{root.as_posix()}"] with trust_level = '
        f'"trusted" to {_CONFIG_PATH} yourself, then rerun this check.'
    )


def main() -> None:
    root = repo_root()
    if root is None:
        print("cannot resolve the current git repository root", file=sys.stderr)
        raise SystemExit(2)
    if not _CONFIG_PATH.exists():
        print(
            f"{_CONFIG_PATH} does not exist; Codex has never recorded a trust "
            f"decision for any project. {_remediation(root)}",
            file=sys.stderr,
        )
        raise SystemExit(1)
    try:
        config = tomllib.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        print(f"cannot read or parse {_CONFIG_PATH}: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    if is_trusted(config, root):
        print(f"ok: {root} is trusted in {_CONFIG_PATH}")
        return
    print(
        f"{root} is not marked trusted in {_CONFIG_PATH}; Codex will not load "
        f"this repository's hooks.json. {_remediation(root)}",
        file=sys.stderr,
    )
    raise SystemExit(1)


if __name__ == "__main__":
    main()
