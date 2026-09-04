"""Preflight whether Codex CLI trusts this project before its hooks load at all.

Codex loads a project's `.codex/` layer — `hooks.json` included — only for a
directory the operator has recorded as trusted in `config.toml` under
`$CODEX_HOME` (default `~/.codex`, `%USERPROFILE%\\.codex` on Windows), in a
`[projects."<absolute-repo-path>"]` table with `trust_level = "trusted"`. An
untrusted checkout silently skips every project hook, including the `Stop`
turn-boundary gate (ADR 0021): an adopter can follow every documented step
and still never have it run. This check is read-only and makes that
otherwise-invisible prerequisite an explicit, scriptable preflight instead of
an assumption.

Project trust is necessary but not sufficient. Codex CLI gates hook
*execution* behind a second, separate approval — persisted per-hook in the
same `config.toml`'s `[hooks.state]` table as `{enabled, trusted_hash}`,
where `trusted_hash` is compared against an internally computed hash of the
hook's current definition. That comparison uses a private, unversioned
algorithm with no supported non-interactive read path (no `codex doctor`
field, no `codex hooks` subcommand, no documented `--json` output covers it
as of Codex CLI 0.144.0-alpha.4) — only the interactive TUI's "Hooks need
review" prompt and `--dangerously-bypass-hook-trust` observe it. This script
does not attempt to compute or infer hook-trust state: a best-effort guess
built on an undocumented hash would itself be a new false-positive source,
the exact failure this preflight exists to prevent. It reports project trust
only, and says so on success.

Exit 0 means the current repository is trusted (project trust only — see
above). Exit 1 means it is not (no matching entry, or one present but not
`trusted`). Exit 2 means the git root or `config.toml` could not be resolved
or parsed.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tomllib
from pathlib import Path


def _config_path() -> Path:
    """`$CODEX_HOME/config.toml`, falling back to `~/.codex/config.toml`."""
    codex_home = os.environ.get("CODEX_HOME")
    home = Path(codex_home) if codex_home else Path.home() / ".codex"
    return home / "config.toml"


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


def _remediation(root: Path, config_path: Path) -> str:
    return (
        "Run `codex` once inside this repository and accept its folder-trust "
        f'prompt, or add [projects."{root.as_posix()}"] with trust_level = '
        f'"trusted" to {config_path} yourself, then rerun this check.'
    )


def main() -> None:
    root = repo_root()
    if root is None:
        print("cannot resolve the current git repository root", file=sys.stderr)
        raise SystemExit(2)
    config_path = _config_path()
    if not config_path.exists():
        print(
            f"{config_path} does not exist; Codex has never recorded a trust "
            f"decision for any project. {_remediation(root, config_path)}",
            file=sys.stderr,
        )
        raise SystemExit(1)
    try:
        config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        print(f"cannot read or parse {config_path}: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    if is_trusted(config, root):
        print(
            f"ok: {root} is trusted (project trust) in {config_path}. This does "
            "not confirm hook trust - Codex CLI requires a separate, per-hook "
            "approval before it will run anything from .codex/hooks.json, and "
            "there is no reliable non-interactive way to check that from "
            "outside Codex. Run `codex` once in this repository and confirm no "
            '"Hooks need review" prompt appears, or pass '
            "--dangerously-bypass-hook-trust for unattended invocations that "
            "already vet the hook source."
        )
        return
    print(
        f"{root} is not marked trusted in {config_path}; Codex will not load "
        f"this repository's hooks.json. {_remediation(root, config_path)}",
        file=sys.stderr,
    )
    raise SystemExit(1)


if __name__ == "__main__":
    main()
