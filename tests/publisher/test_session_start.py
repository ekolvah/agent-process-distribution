"""The plugin's session-start hook: its environment, the release drift and the agent identity."""

from __future__ import annotations

import importlib.util
import json
import shlex
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from types import ModuleType
from typing import Callable

import pytest

from tests.publisher.init_harness import CURRENT, load_init
from tests.publisher.plugin_harness import plugin_hooks, run_plugin_hook

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "skills" / "agent-process" / "scripts"


ENV_MARKER = "agent-process plugin environment not installed"


def _session_start(
    tmp_path: Path, manifest: str, **extra: str | None
) -> tuple[subprocess.CompletedProcess, Path | None]:
    """Run the plugin's one `SessionStart` command with a plugin root whose runtime manifest is
    `manifest`, the data directory `tmp_path/data` and a fresh env file; return the result and
    the interpreter the env file exports, if any."""
    hooks = [
        hook for group in plugin_hooks()["hooks"].get("SessionStart", []) for hook in group["hooks"]
    ]
    assert len(hooks) == 1, hooks
    assert hooks[0]["timeout"] == 300
    plugin = tmp_path / "plugin"
    scripts = plugin / "skills" / "agent-process" / "scripts"
    scripts.mkdir(parents=True, exist_ok=True)
    shutil.copy(SCRIPTS / "plugin_env.py", scripts / "plugin_env.py")
    (plugin / ".agent-process").mkdir(exist_ok=True)
    (plugin / ".agent-process" / "requirements.txt").write_text(manifest, encoding="utf-8")
    env_file = tmp_path / "session-env.sh"
    env_file.unlink(missing_ok=True)
    variables: dict[str, str | None] = {
        "CLAUDE_PLUGIN_ROOT": plugin.as_posix(),
        "CLAUDE_PLUGIN_DATA": (tmp_path / "data").as_posix(),
        "CLAUDE_ENV_FILE": env_file.as_posix(),
        **extra,
    }
    project = tmp_path / "project"
    project.mkdir(exist_ok=True)
    payload = {"hook_event_name": "SessionStart", "source": "startup"}
    result = run_plugin_hook(project, hooks[0]["command"], payload, variables)
    lines = env_file.read_text(encoding="utf-8").splitlines() if env_file.exists() else []
    exports = [
        shlex.split(line.removeprefix("export AGENT_PROCESS_PYTHON="))[0]
        for line in lines
        if line.startswith("export AGENT_PROCESS_PYTHON=")
    ]
    assert len(exports) <= 1, lines
    return result, Path(exports[0]) if exports else None


def _environment(tmp_path: Path, interpreter: Path | None) -> Path:
    """The completed `venv-*` directory of the data directory that `interpreter` belongs to."""
    assert interpreter is not None and interpreter.is_file(), interpreter
    venv = tmp_path / "data" / interpreter.relative_to(tmp_path / "data").parts[0]
    assert venv.name.startswith("venv-"), venv
    assert (venv / ".complete").is_file(), venv
    return venv


def test_session_start_installs_the_plugin_environment(tmp_path: Path) -> None:
    """Scenarios: First session, Manifest unchanged, Broken environment."""
    result, interpreter = _session_start(tmp_path, "# nothing to download\n")
    assert (result.returncode, result.stdout) == (0, ""), result.stderr
    venv = _environment(tmp_path, interpreter)
    built = (venv / "pyvenv.cfg").stat().st_mtime_ns

    result, again = _session_start(tmp_path, "# nothing to download\n")
    assert (result.returncode, result.stdout) == (0, ""), result.stderr
    assert again == interpreter
    assert (venv / "pyvenv.cfg").stat().st_mtime_ns == built

    assert interpreter is not None
    interpreter.unlink()
    result, rebuilt = _session_start(tmp_path, "# nothing to download\n")
    assert (result.returncode, result.stdout) == (0, ""), result.stderr
    assert rebuilt == interpreter
    assert _environment(tmp_path, rebuilt) == venv


def test_session_start_keeps_the_previous_environment(tmp_path: Path) -> None:
    """Scenario: Manifest changed."""
    _, first = _session_start(tmp_path, "# first\n")
    old = _environment(tmp_path, first)
    built = (old / "pyvenv.cfg").stat().st_mtime_ns
    completed = (old / ".complete").stat().st_mtime_ns
    result, second = _session_start(tmp_path, "# second\n")
    assert (result.returncode, result.stdout) == (0, ""), result.stderr
    assert _environment(tmp_path, second) != old
    assert (old / "pyvenv.cfg").stat().st_mtime_ns == built
    assert (old / ".complete").stat().st_mtime_ns == completed


@pytest.mark.parametrize(
    ("manifest", "extra", "named", "runs"),
    [
        pytest.param(
            "agent-process-no-such-package==0\n",
            {"PIP_NO_INDEX": "1"},
            "agent-process-no-such-package",
            2,
            id="pip",
        ),
        pytest.param("# none\n", {"CLAUDE_PLUGIN_DATA": None}, "CLAUDE_PLUGIN_DATA", 1, id="data"),
        pytest.param("# none\n", {"CLAUDE_ENV_FILE": None}, "CLAUDE_ENV_FILE", 1, id="env-file"),
    ],
)
def test_session_start_reports_a_missing_environment(
    tmp_path: Path, manifest: str, extra: dict[str, str | None], named: str, runs: int
) -> None:
    """Scenarios: Install fails, Hook variables absent; a failed install is retried."""
    for _ in range(runs):
        result, interpreter = _session_start(tmp_path, manifest, **extra)
        assert result.returncode == 0, result.stderr
        output = json.loads(result.stdout)
        context = output["hookSpecificOutput"]["additionalContext"]
        for text in (output["systemMessage"], context):
            assert ENV_MARKER in text and named in text, text
        assert interpreter is None
        assert not list((tmp_path / "data").glob("venv-*/.complete"))


DRIFT_MARKER = "agent-process release drift"


def _config_block(recorded: str) -> str:
    """The installer's config block with the release line `recorded`."""
    init = load_init()
    block, line = init.render_config_block(), init.RELEASE + CURRENT
    assert line in block, "the rendered block records no release"
    return block.replace(line, init.RELEASE + recorded)


def _start_in_project(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    via_cwd: bool = False,
) -> str:
    """`plugin_env.main` for `session-start` in-process at the project `tmp_path/project`, named
    by `CLAUDE_PROJECT_DIR` or, `via_cwd`, by the current directory; without
    `CLAUDE_PLUGIN_DATA`, so nothing installs. No git config of the machine applies, so the
    identity export finds no bot and never calls `gh`; its env file is `tmp_path/env.sh`.
    Returns its stdout."""
    module, _ = _plugin_env(tmp_path, lambda *_: None)
    project = tmp_path / "project"
    project.mkdir(exist_ok=True)
    empty = tmp_path / "gitconfig"
    empty.write_text("", encoding="utf-8")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(empty))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("CLAUDE_ENV_FILE", str(tmp_path / "env.sh"))
    monkeypatch.syspath_prepend(str(SCRIPTS))  # as `python plugin_env.py` puts its directory first
    monkeypatch.delenv("CLAUDE_PLUGIN_DATA", raising=False)
    monkeypatch.setattr(sys, "argv", ["plugin_env.py", "session-start"])
    if via_cwd:
        monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
        monkeypatch.chdir(project)
    else:
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(project))
    assert module.main() == 0
    return capsys.readouterr().out


def _texts(stdout: str) -> tuple[str, str]:
    output = json.loads(stdout)
    return output["systemMessage"], output["hookSpecificOutput"]["additionalContext"]


@pytest.mark.parametrize("via_cwd", [False, True], ids=["project-dir", "cwd"])
def test_session_start_reports_release_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    via_cwd: bool,
) -> None:
    """Scenario: Repository behind the plugin."""
    config = tmp_path / "project" / "openspec" / "config.yaml"
    config.parent.mkdir(parents=True)
    config.write_text(_config_block("3.29.0"), encoding="utf-8")
    stdout = _start_in_project(tmp_path, monkeypatch, capsys, via_cwd)
    for text in _texts(stdout):
        for named in (DRIFT_MARKER, "3.29.0", CURRENT, "/agent-process:init"):
            assert named in text, text


@pytest.mark.parametrize("config", ["current", "no-block", "no-config"])
def test_session_start_silent_on_release(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    config: str,
) -> None:
    """Scenario: Release current or not installed."""
    path = tmp_path / "project" / "openspec" / "config.yaml"
    if config != "no-config":
        path.parent.mkdir(parents=True)
        text = _config_block(CURRENT) if config == "current" else "schema: x\n"
        path.write_text(text, encoding="utf-8")
    stdout = _start_in_project(tmp_path, monkeypatch, capsys)
    for text in _texts(stdout):
        assert ENV_MARKER in text and DRIFT_MARKER not in text, text


def test_session_start_release_undecidable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Scenario: Release undecidable."""
    (tmp_path / "project" / "openspec" / "config.yaml").mkdir(parents=True)
    stdout = _start_in_project(tmp_path, monkeypatch, capsys)
    for text in _texts(stdout):
        assert DRIFT_MARKER in text and "cannot check" in text, text


IDENTITY_MARKER = "agent-process agent identity not set"
IDENTITY_FIX = "Install step 5 of the agent-process skill"
AGENT_TOKEN = "fake-token-123"
Done = subprocess.CompletedProcess


class FakeCommands:
    """`git` and `gh` as the session-start identity export runs them in the project: the key
    `agent-process.bot` is `bot`, `gh` holds `AGENT_TOKEN` for it, and the permission read
    answers `permission` for a call carrying that token. `faults` replaces the answer of the
    command it names (`bot`, `token`, `view`)."""

    def __init__(self, permission: str = "WRITE", **faults: Done) -> None:
        self.permission = permission
        self.faults = faults

    def __call__(self, program: str, *args: str, env: dict[str, str] | None = None) -> Done:
        command = (program, *args)
        if command == ("git", "config", "--get", "agent-process.bot"):
            return self.faults.get("bot") or Done(command, 0, "bot\n", "")
        if command == ("gh", "auth", "token", "--user", "bot"):
            return self.faults.get("token") or Done(command, 0, f"{AGENT_TOKEN}\n", "")
        assert command == ("gh", "repo", "view", "--json", "viewerPermission"), command
        if "view" in self.faults:
            return self.faults["view"]
        if (env or {}).get("GH_TOKEN") != AGENT_TOKEN:
            return Done(command, 1, "", "HTTP 401: Bad credentials\n")
        return Done(command, 0, json.dumps({"viewerPermission": self.permission}), "")


def _export_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, commands: FakeCommands, env_file: bool = True
) -> tuple[str | None, list[str]]:
    """`plugin_env`'s identity export over `commands`; its marker and the env file's lines."""
    module, _ = _plugin_env(tmp_path, lambda *_: None)
    monkeypatch.syspath_prepend(str(SCRIPTS))
    path = tmp_path / "env.sh"
    marker = module.export_identity(commands, str(path) if env_file else None)
    return marker, path.read_text(encoding="utf-8").splitlines() if path.exists() else []


def test_session_start_takes_the_agent_token(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Scenario: Token taken."""
    marker, lines = _export_identity(tmp_path, monkeypatch, FakeCommands())
    assert marker is None, marker
    assert lines == [f"export GH_TOKEN={AGENT_TOKEN}"], lines


@pytest.mark.parametrize(
    ("commands", "env_file", "reason"),
    [
        pytest.param(
            FakeCommands(bot=Done((), 1, "", "")),
            True,
            "git config agent-process.bot is not set",
            id="no-bot",
        ),
        pytest.param(
            FakeCommands(
                token=Done((), 1, "", "no oauth token found for github.com account bot\n")
            ),
            True,
            "gh holds no token for bot",
            id="no-token",
        ),
        pytest.param(FakeCommands("READ"), True, "bot has READ permission", id="read"),
        pytest.param(FakeCommands("ADMIN"), True, "bot has ADMIN permission", id="admin"),
        pytest.param(
            FakeCommands(view=Done((), 1, "", "HTTP 502: Bad Gateway\n")),
            True,
            "cannot read bot's permission",
            id="unreadable",
        ),
        pytest.param(FakeCommands(), False, "CLAUDE_ENV_FILE", id="no-env-file"),
    ],
)
def test_session_start_reports_a_missing_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    commands: FakeCommands,
    env_file: bool,
    reason: str,
) -> None:
    """Scenario: Identity missing — the reason and the fix, never the token."""
    marker, lines = _export_identity(tmp_path, monkeypatch, commands, env_file)
    assert not [line for line in lines if "GH_TOKEN" in line], lines
    assert marker is not None
    for named in (IDENTITY_MARKER, reason, IDENTITY_FIX):
        assert named in marker, marker
    assert AGENT_TOKEN not in marker


def test_session_start_reports_the_marker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Scenario: Identity missing — in the hook's output, to the person and to the agent."""
    config = tmp_path / "project" / "openspec" / "config.yaml"
    config.parent.mkdir(parents=True)
    config.write_text(_config_block(CURRENT), encoding="utf-8")
    stdout = _start_in_project(tmp_path, monkeypatch, capsys)
    for text in _texts(stdout):
        for named in (IDENTITY_MARKER, "git config agent-process.bot is not set", IDENTITY_FIX):
            assert named in text, text


def test_session_start_skips_identity_outside_the_block(tmp_path: Path) -> None:
    """Scenario: Project without the block."""
    result, _ = _session_start(tmp_path, "# none\n", CLAUDE_PLUGIN_DATA=None)
    assert result.returncode == 0, result.stderr
    assert IDENTITY_MARKER not in result.stdout, result.stdout
    env_file = tmp_path / "session-env.sh"
    lines = env_file.read_text(encoding="utf-8").splitlines() if env_file.exists() else []
    assert not [line for line in lines if "GH_TOKEN" in line], lines


def test_init_imports_without_site_packages() -> None:
    """Design D2: `init` imports with the standard library alone, as the session-start hook
    imports it before the plugin environment exists."""
    code = f"import sys; sys.path.insert(0, {str(SCRIPTS)!r}); import init"
    result = subprocess.run(
        [sys.executable, "-I", "-S", "-c", code], capture_output=True, encoding="utf-8", check=False
    )
    assert result.returncode == 0, result.stderr


Command = tuple[str, ...]


def _plugin_env(
    tmp_path: Path, before: Callable[[str, Command], None]
) -> tuple[ModuleType, list[tuple[str, Command]]]:
    """`plugin_env` loaded in-process with the manifest `tmp_path/requirements.txt`; its `_run`
    records each command under the calling thread's name, calls `before` and runs it."""
    spec = importlib.util.spec_from_file_location(
        "agent_process_plugin_env_under_test", SCRIPTS / "plugin_env.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    manifest = tmp_path / "requirements.txt"
    manifest.write_text("# none\n", encoding="utf-8")
    log: list[tuple[str, Command]] = []
    run = module._run

    def recorded(*args: str | Path) -> None:
        thread, command = threading.current_thread().name, tuple(str(arg) for arg in args)
        log.append((thread, command))
        before(thread, command)
        run(*args)

    vars(module).update(MANIFEST=manifest, _run=recorded)
    return module, log


def _step(command: Command) -> str:
    """`venv`, `pip install` or `pip check`: the words after `-m`."""
    words = command[command.index("-m") + 1 :]
    return " ".join(words[:2] if words[0] == "pip" else words[:1])


def test_parallel_install_waits_and_reuses_the_environment(tmp_path: Path) -> None:
    """Scenario: Parallel install."""
    data = tmp_path / "data"
    results: dict[str, object] = {}
    b_ran = threading.Event()

    def session(name: str) -> None:
        try:
            python = results[name] = module.install(data)
        except module.InstallError as error:  # reported by the assertions below
            results[name] = error
        else:
            if name == "A":
                results["built"] = (python.parents[1] / "pyvenv.cfg").stat().st_mtime_ns

    a = threading.Thread(target=session, args=("A",), name="A")
    b = threading.Thread(target=session, args=("B",), name="B")

    def before(thread: str, command: Command) -> None:
        if thread == "B":
            b_ran.set()
        elif _step(command) == "pip install" and b.ident is None:
            b.start()
            b_ran.wait(5)

    module, log = _plugin_env(tmp_path, before)
    a.start()
    a.join()
    if b.ident is not None:
        b.join()
    b_steps = [(i, _step(command)) for i, (thread, command) in enumerate(log) if thread == "B"]
    a_last = max(i for i, (thread, _) in enumerate(log) if thread == "A")
    assert [step for _, step in b_steps] == ["pip check"], log
    assert b_steps[0][0] > a_last, log
    assert isinstance(results["A"], Path), results
    assert results["B"] == results["A"], results
    venv = results["A"].parents[1]
    assert (venv / "pyvenv.cfg").stat().st_mtime_ns == results["built"]


def test_install_reports_a_lock_held_too_long(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Scenario: Install waits too long."""
    data = tmp_path / "data"
    reached, release = threading.Event(), threading.Event()

    def before(thread: str, command: Command) -> None:
        if thread == "A" and _step(command) == "pip install" and not reached.is_set():
            reached.set()
            release.wait(10)

    module, log = _plugin_env(tmp_path, before)
    wait = getattr(module, "LOCK_WAIT", None)
    monkeypatch.setattr(module, "LOCK_WAIT", 1, raising=False)
    a = threading.Thread(target=lambda: module.install(data), name="A")
    a.start()
    try:
        reached.wait(5)
        me = threading.current_thread().name
        with pytest.raises(module.InstallError) as caught:
            module.install(data)
        assert ".lock" in str(caught.value) and "1 s" in str(caught.value), caught.value
        assert [command for thread, command in log if thread == me] == [], log
        assert wait == 240
    finally:
        release.set()
        a.join(60)
