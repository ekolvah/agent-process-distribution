"""Plugin environment: install the plugin's runtime manifest at session start (#309).

The scripts run under whatever `python` the session finds, and a consumer's lacks `jsonschema`.
Claude Code documents the remedy: a `SessionStart` hook installs dependencies into
`${CLAUDE_PLUGIN_DATA}`, which survives plugin updates. The environment is named by the
manifest's content, so a new manifest never touches the environment a parallel session uses;
an existing one is rebuilt only when it has no `.complete` or its interpreter fails `pip check`.
The hook exports `AGENT_PROCESS_PYTHON` through `CLAUDE_ENV_FILE`, which reaches the Bash tool,
and `bin/agent-process` runs scripts with it.

A failure, or a hook run without either variable, prints the session-start marker JSON and
writes nothing, so the launcher falls back to `python` and the next session retries.

The plugin's `hooks/hooks.json` runs it as `python <plugin>/.../plugin_env.py session-start`.
"""

from __future__ import annotations

import hashlib
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[3]
MANIFEST = PLUGIN_ROOT / ".agent-process" / "requirements.txt"
MARKER = "agent-process plugin environment not installed"


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


def install(data: Path) -> Path:
    """The interpreter of the manifest's completed environment, installing it when needed."""
    digest = hashlib.sha256(MANIFEST.read_bytes()).hexdigest()[:12]
    venv = data / f"venv-{digest}"
    python = interpreter(venv)
    if (venv / ".complete").is_file():
        try:
            _run(python, "-m", "pip", "check")
            return python
        except InstallError:
            pass
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


def main() -> int:
    if sys.argv[1:] != ["session-start"]:
        print("usage: plugin_env.py session-start", file=sys.stderr)
        return 2
    cause = session_start()
    if cause is not None:
        text = f"{MARKER}: {cause}. Scripts run under `python` until a session installs it."
        output = {
            "systemMessage": text,
            "hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": text},
        }
        print(json.dumps(output))  # ASCII escapes: a Windows console encoding cannot fail
    return 0


if __name__ == "__main__":
    sys.exit(main())
