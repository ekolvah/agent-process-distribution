"""Plugin environment: install the plugin's runtime manifest at session start.

The scripts run under whatever `python` the session finds, and a consumer's lacks `jsonschema`.
Claude Code documents the remedy: a `SessionStart` hook installs dependencies into
`${CLAUDE_PLUGIN_DATA}`, which survives plugin updates. The environment is named by the
manifest's content, so a new manifest never touches the environment a parallel session uses;
an existing one is rebuilt only when it has no `.complete` or its interpreter fails `pip check`.
Sessions build one at a time under an exclusive lock on `${CLAUDE_PLUGIN_DATA}/.lock` and check
again under it, so a session that waited reuses what the other built; a wait longer than
`LOCK_WAIT` seconds fails the install.
The hook exports `AGENT_PROCESS_PYTHON` through `CLAUDE_ENV_FILE`, which reaches the Bash tool,
and `bin/agent-process` runs scripts with it.

A failure, or a hook run without either variable, prints the session-start marker JSON and
writes nothing, so the launcher falls back to `python` and the next session retries.

In a project whose `openspec/config.yaml` holds the agent-process block (`CLAUDE_PROJECT_DIR`,
else the current directory), the hook also runs `init.release_drift`, the check of
`start_change`, and prints `agent-process release drift` with its message, or with `cannot
check` and the reason. There it also exports `GH_TOKEN` through `CLAUDE_ENV_FILE`: the token
`gh` holds for the login `git config agent-process.bot` names, when that token can write to the
repository (`manual.agent_token`); otherwise it prints `agent-process agent identity not set`
with the reason and the fix, and the session runs as `gh`'s active account. `init` and `manual`
import only the standard library, so they run before the environment exists. All markers share
one JSON, a `systemMessage` line each.

The plugin's `hooks/hooks.json` runs it as `python <plugin>/.../plugin_env.py session-start`.
"""

from __future__ import annotations

import hashlib
import json
import os
import shlex
import shutil
import subprocess
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING

if sys.platform == "win32":
    import msvcrt

    HELD: type[OSError] = PermissionError  # what a lock another handle holds raises
else:
    import fcntl

    HELD = BlockingIOError

if TYPE_CHECKING:
    import manual

PLUGIN_ROOT = Path(__file__).resolve().parents[3]
MANIFEST = PLUGIN_ROOT / ".agent-process" / "requirements.txt"
MARKER = "agent-process plugin environment not installed"
DRIFT_MARKER = "agent-process release drift"
IDENTITY_MARKER = "agent-process agent identity not set"
BEGIN = "# agent-process:begin"  # the first line of the installer's config block
LOCK_WAIT = 240  # seconds; below the hook's timeout of 300, so the marker reaches the session


class InstallError(Exception):
    """A step that left the environment incomplete; the message is its cause."""


def _run(*args: str | Path) -> None:
    try:
        result = subprocess.run(
            [str(arg) for arg in args], capture_output=True, encoding="utf-8", check=False
        )
    except OSError as error:
        raise InstallError(str(error)) from error
    if result.returncode != 0:
        lines = [line for line in (result.stderr or result.stdout or "").splitlines() if line]
        command = " ".join(str(arg) for arg in args)
        raise InstallError(lines[-1] if lines else f"{command} exited {result.returncode}")


def interpreter(venv: Path) -> Path:
    return venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


@contextmanager
def _locked(path: Path) -> Iterator[None]:
    """Hold an exclusive lock on `path`, polling each second for at most `LOCK_WAIT` seconds;
    any error but `HELD` propagates. The OS releases the lock of a killed holder."""
    with open(path, "a+b") as handle:
        deadline = time.monotonic() + LOCK_WAIT
        while True:
            try:
                if sys.platform == "win32":
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except HELD:
                if time.monotonic() >= deadline:
                    raise InstallError(f"another session held {path} for {LOCK_WAIT} s") from None
                time.sleep(1)
        try:
            yield
        finally:
            if sys.platform == "win32":
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _usable(venv: Path) -> bool:
    if not (venv / ".complete").is_file():
        return False
    try:
        _run(interpreter(venv), "-m", "pip", "check")
    except InstallError:
        return False
    return True


def install(data: Path) -> Path:
    """The interpreter of the manifest's completed environment, installing it when needed."""
    digest = hashlib.sha256(MANIFEST.read_bytes()).hexdigest()[:12]
    venv = data / f"venv-{digest}"
    python = interpreter(venv)
    if _usable(venv):
        return python
    data.mkdir(parents=True, exist_ok=True)
    with _locked(data / ".lock"):
        if _usable(venv):  # another session built it while this one waited
            return python
        (venv / ".complete").unlink(missing_ok=True)
        _run(sys.executable, "-m", "venv", "--clear", venv)
        _run(python, "-m", "pip", "install", "--disable-pip-version-check", "-q", "-r", MANIFEST)
        (venv / ".complete").write_text("", encoding="utf-8")
    return python


def session_start() -> str | None:
    """Install and export; the cause of the failure, or None."""
    for name in ("CLAUDE_PLUGIN_DATA", "CLAUDE_ENV_FILE"):
        if not os.environ.get(name):
            return f"the hook received no {name}"
    try:
        python = install(Path(os.environ["CLAUDE_PLUGIN_DATA"]))
    except InstallError as error:
        return str(error)
    with open(os.environ["CLAUDE_ENV_FILE"], "a", encoding="utf-8") as exports:
        exports.write(f"export AGENT_PROCESS_PYTHON={shlex.quote(python.as_posix())}\n")
    return None


def _has_block(project: Path) -> bool:
    """The project's `openspec/config.yaml` holds the agent-process block; a read error raises."""
    text = (project / "openspec" / "config.yaml").read_text(encoding="utf-8")
    return BEGIN in (line.strip() for line in text.splitlines())


def release_drift(project: Path) -> str | None:
    """The drift marker of the project's recorded release, or None when the project has no
    agent-process block or records this plugin's release."""
    try:
        if not _has_block(project):
            return None
        import init  # after the gate: a project without the block never pays for the import

        drift = init.release_drift(project, Path(__file__).resolve().parent)
    except FileNotFoundError:
        return None
    except (OSError, UnicodeError, ImportError) as error:  # a visible degraded marker
        return f"{DRIFT_MARKER}, cannot check: {error}"
    return None if drift is None else f"agent-process {drift}"


def _commands_in(project: Path) -> manual.Run:
    """`manual.Run` in `project`; a program that cannot start raises `OSError` naming it."""

    def run(
        program: str, *args: str, env: dict[str, str] | None = None
    ) -> subprocess.CompletedProcess[str]:
        try:
            return subprocess.run(
                [shutil.which(program) or program, *args],
                cwd=project,
                env=env,
                capture_output=True,
                encoding="utf-8",
                check=False,
            )
        except OSError as error:
            raise OSError(f"{program} cannot run: {error}") from error

    return run


def export_identity(run: manual.Run, env_file: str | None) -> str | None:
    """Append the agent's `GH_TOKEN` to `env_file`; the identity marker, or None. The token is
    in no output."""
    import manual  # after the block gate, as `init`

    try:
        if not env_file:
            raise manual.NoAgentToken("the hook received no CLAUDE_ENV_FILE")
        token = manual.agent_token(run)
        with open(env_file, "a", encoding="utf-8") as exports:
            exports.write(f"export GH_TOKEN={shlex.quote(token)}\n")
    except manual.NoAgentToken as error:
        reason = str(error)
    except manual.Unreadable as error:
        reason = f"cannot read {error}"
    except OSError as error:
        reason = str(error)
    else:
        return None
    return f"{IDENTITY_MARKER} ({reason}) — fix: {manual.IDENTITY_FIX}"


def agent_identity(project: Path) -> str | None:
    """The identity marker of a project with the block, or None; `release_drift` reports a
    config it cannot read."""
    try:
        if not _has_block(project):
            return None
    except (OSError, UnicodeError):
        return None
    try:
        return export_identity(_commands_in(project), os.environ.get("CLAUDE_ENV_FILE"))
    except ImportError as error:
        return f"{IDENTITY_MARKER} (cannot import manual: {error})"


def main() -> int:
    if sys.argv[1:] != ["session-start"]:
        print("usage: plugin_env.py session-start", file=sys.stderr)
        return 2
    texts = []
    cause = session_start()
    if cause is not None:
        texts.append(f"{MARKER}: {cause}. Scripts run under `python` until a session installs it.")
    project = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    texts += [text for text in (release_drift(project), agent_identity(project)) if text]
    if texts:
        output = {
            "systemMessage": "\n".join(texts),
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": " ".join(texts),
            },
        }
        print(json.dumps(output))  # ASCII escapes: a Windows console encoding cannot fail
    return 0


if __name__ == "__main__":
    sys.exit(main())
