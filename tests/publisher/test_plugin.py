"""The shared package boundary: the procedure, its scripts, and the installer's templates."""

from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
import tomllib
from pathlib import Path

import pytest
import yaml

from tests.publisher.init_harness import load_init
from tests.publisher.lint_harness import FINDING, edit_payload, lint_repo

ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / ".claude-plugin" / "plugin.json"
MARKETPLACE = ROOT / ".claude-plugin" / "marketplace.json"
SETTINGS = ROOT / ".claude" / "settings.json"
SKILL = ROOT / "skills" / "agent-process" / "SKILL.md"
PACKAGE = SKILL.parent
PRINCIPLES = PACKAGE / "principles.md"
SCRIPTS = PACKAGE / "scripts"
MOVED_SCRIPTS = {
    "activate_protection.py",
    "archive_change.py",
    "check_red.py",
    "create_tracking_issue.py",
    "edit_lint.py",
    "init.py",
    "manual.py",
    "memory_checkpoint.py",
    "navigation_policy.py",
    "onboarding.py",
    "plugin_env.py",
    "quality.py",
    "resolve_review_thread.py",
    "set_status.py",
    "start_change.py",
    "steps.py",
    "wait_for_pr.py",
}

TEMPLATES = {
    "agent-process-quality.json",
    "agent-process.yml",
    "agent-review.yml",
    "config.yaml",
    "dependabot.yml",
    "pre-commit-config.yaml",
    "ruleset.json",
    "settings.json",
    "skill_check.py",
}


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_shared_skill_owns_the_procedure_and_scripts() -> None:
    text = SKILL.read_text(encoding="utf-8")
    assert text.startswith("---\nname: agent-process\n")
    for heading in (
        "## Proposal",
        "## Specifications",
        "## Design",
        "## Tasks",
        "## Architect review",
        "## Delivery",
    ):
        assert heading in text
    assert {path.name for path in SCRIPTS.glob("*.py")} == MOVED_SCRIPTS
    for name in MOVED_SCRIPTS:
        assert not (ROOT / ".agent-process" / "scripts" / name).exists()


def _section(text: str, heading: str) -> str:
    start = text.index(heading) + len(heading)
    end = text.find("\n## ", start)
    return text[start : end if end != -1 else len(text)]


def test_skill_carries_principles_core_and_harness_tactics() -> None:
    """Scenario: A consumer reads principles and tactics from the skill."""
    text = SKILL.read_text(encoding="utf-8").split("\n## Proposal")[0]
    assert "\n## Principles\n" in text
    assert "\n## Claude harness\n" in text
    core = _section(text, "\n## Principles\n")
    for goal in ("bug-fixing", "token spend", "user control"):
        assert goal in core
    headings = re.findall(
        r"^### (VII|VI|V|IV|III|II|I)\. (.+)$", PRINCIPLES.read_text("utf-8"), re.M
    )
    assert [numeral for numeral, _ in headings] == ["I", "II", "III", "IV", "V", "VI", "VII"]
    for numeral, title in headings:
        # GitHub's heading anchor: lower case, punctuation dropped, spaces to hyphens.
        anchor = re.sub(r"[^\w\s-]", "", f"{numeral}. {title}".lower()).replace(" ", "-")
        assert f"](principles.md#{anchor})" in core
    harness = _section(text, "\n## Claude harness\n")
    assert "gh issue view" in harness
    assert "git branch --show-current" in harness
    assert "/compact" not in harness


def test_package_contents_are_closed() -> None:
    relative_files = {
        path.relative_to(PACKAGE).as_posix()
        for path in PACKAGE.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    }
    assert relative_files == (
        {"SKILL.md", "architect-review.schema.json", "principles.md"}
        | {f"scripts/{name}" for name in MOVED_SCRIPTS}
        | {f"templates/{name}" for name in TEMPLATES}
    )
    forbidden = ("hook",)
    assert not any(token in path.lower() for path in relative_files for token in forbidden)


def _package_text_files() -> list[Path]:
    roots = (PACKAGE, ROOT / "agents", ROOT / "commands", ROOT / "hooks")
    return sorted(
        path
        for root in roots
        for path in root.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    )


def test_package_paths_resolve_in_a_consumer() -> None:
    """A consumer has no `.agent-process/`; the plugin lives outside its repository."""
    findings = []
    for path in _package_text_files():
        text = path.read_text(encoding="utf-8")
        name = path.relative_to(ROOT).as_posix()
        findings += [f"{name}: {m.group()}" for m in re.finditer(r"\.agent-process/\S*", text)]
        if path.suffix == ".md" and PACKAGE in path.parents:
            for target in re.findall(r"\]\(([^)#\s]+)", text):
                if "://" in target:
                    continue
                if PACKAGE.resolve() not in (path.parent / target).resolve().parents:
                    findings.append(f"{name}: link {target} leaves the skill directory")
        if path.parent == ROOT / "agents":
            findings += _agent_package_path_findings(name, text)
    assert not findings, "\n".join(findings)


def _agent_package_path_findings(name: str, text: str) -> list[str]:
    findings = []
    if "skills/agent-process/" in text:
        if "${CLAUDE_PLUGIN_ROOT}/skills/agent-process/" not in text:
            findings.append(f"{name}: skills/agent-process/ without ${{CLAUDE_PLUGIN_ROOT}}")
    # The whole skill directory ships, so a named package file resolves in either root.
    for tail in re.findall(r"skills/agent-process/([\w./-]*[\w-])", text):
        if not (PACKAGE / tail).is_file():
            findings.append(f"{name}: skills/agent-process/{tail} is not a package file")
    return findings


def test_agent_package_paths_are_checked_per_occurrence() -> None:
    """One valid fallback does not cover another package path of the same agent."""
    text = (ROOT / "agents" / "architect-reviewer.md").read_text(encoding="utf-8")
    assert not _agent_package_path_findings("reviewer", text)
    added = text + "\nRead `skills/agent-process/new.md`.\n"
    assert _agent_package_path_findings("reviewer", added) == [
        "reviewer: skills/agent-process/new.md is not a package file"
    ]


def test_plugin_agents_inherit_the_session_model() -> None:
    """A pinned model goes stale; an agent runs on the chat's model and effort."""
    agents = sorted((ROOT / "agents").glob("*.md"))
    assert agents
    for path in agents:
        frontmatter = yaml.safe_load(path.read_text(encoding="utf-8").split("---")[1])
        assert frontmatter["model"] == "inherit", path.name
        assert "effort" not in frontmatter, path.name


def test_publisher_dogfoods_process() -> None:
    settings = _json(SETTINGS)
    assert settings["extraKnownMarketplaces"] == {
        "agent-process-marketplace": {
            "source": {
                "source": "github",
                "repo": "ekolvah/agent-process-distribution",
            }
        }
    }
    assert "enabledPlugins" not in settings
    commands = [
        hook["command"] for group in settings["hooks"]["SessionStart"] for hook in group["hooks"]
    ]
    assert any("skills/agent-process/templates/skill_check.py" in c for c in commands)
    config = yaml.safe_load((ROOT / "openspec" / "config.yaml").read_text(encoding="utf-8"))
    assert all(
        "skills/agent-process/SKILL.md" in " ".join(rule) for rule in config["rules"].values()
    )


COMPONENT_ROOTS = [".claude-plugin", "agents", "bin", "commands", "hooks", "skills/agent-process"]
# The default locations of the plugin reference's "Standard layout", plus the manifest directory.
DEFAULT_LOCATIONS = [
    ".claude-plugin",
    "SKILL.md",
    "commands",
    "agents",
    "hooks",
    ".mcp.json",
    ".lsp.json",
    "output-styles",
    "workflows",
    "themes",
    "monitors",
    "bin",
    "settings.json",
]


def _component_roots() -> list[str]:
    """The plugin component roots the repository has at its top level."""
    roots = [name for name in DEFAULT_LOCATIONS if (ROOT / name).exists()]
    roots += [f"skills/{path.name}" for path in (ROOT / "skills").iterdir() if path.is_dir()]
    return sorted(roots)


def test_plugin_component_roots_are_closed() -> None:
    """Scenario: Component roots — nothing but the package acts in a whole-cloned consumer."""
    roots = _component_roots()
    extra = sorted(set(roots) - set(COMPONENT_ROOTS))
    missing = sorted(set(COMPONENT_ROOTS) - set(roots))
    assert not extra and not missing, f"extra component roots {extra}, missing {missing}"


def test_marketplace_source_is_whole() -> None:
    """Scenario: Settings render — the marketplace source names no `sparsePaths`."""
    init = load_init()
    rendered = init._render_settings(init.VERSION)
    for settings in (rendered, _json(SETTINGS)):
        source = settings["extraKnownMarketplaces"]["agent-process-marketplace"]["source"]
        assert "sparsePaths" not in source


LAUNCHER = ROOT / "bin" / "agent-process"
PROBE = "import sys\nprint({where!r}, sys.argv[1:])\nsys.exit(3)\n"


def _run_launcher(
    tmp_path: Path, cwd: Path, args: str, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    """Run the bare command as the Bash tool does: `sh -c`, the plugin's `bin/` on `PATH`."""
    plugin = tmp_path / "plugin"
    (plugin / "bin").mkdir(parents=True, exist_ok=True)
    shutil.copy(LAUNCHER, plugin / "bin" / "agent-process")
    (plugin / "bin" / "agent-process").chmod(0o755)
    scripts = plugin / "skills" / "agent-process" / "scripts"
    scripts.mkdir(parents=True, exist_ok=True)
    (scripts / "probe.py").write_text(PROBE.format(where="plugin"), encoding="utf-8")
    sh = shutil.which("sh")
    assert sh, "sh is not on PATH"
    path = os.pathsep.join([str(plugin / "bin"), os.environ["PATH"]])
    cwd.mkdir(parents=True, exist_ok=True)
    return subprocess.run(
        [sh, "-c", f"agent-process {args}"],
        cwd=cwd,
        env={**os.environ, "PATH": path, **(env or {})},
        capture_output=True,
        encoding="utf-8",
        check=False,
    )


def test_launcher_runs_the_plugin_script_from_a_consumer(tmp_path: Path) -> None:
    """Scenario: Printed command in a consumer."""
    result = _run_launcher(tmp_path, tmp_path / "consumer", "probe a 'b c'")
    assert result.returncode == 3, result.stderr
    assert result.stdout.strip() == "plugin ['a', 'b c']"


OPENSPEC_LAUNCHER = ROOT / "bin" / "openspec"
FAKE_NPX = "#!/bin/sh\nprintf '[%s]' \"$@\"\nexit 3\n"
OPENSPEC_PIN = re.compile(r"@fission-ai/openspec@([0-9A-Za-z][^\s\"'`)]*)")


def test_bare_openspec_runs_the_pin(tmp_path: Path) -> None:
    """Scenario: Bare command."""
    plugin_bin = tmp_path / "plugin" / "bin"
    fake = tmp_path / "fake"
    plugin_bin.mkdir(parents=True)
    fake.mkdir()
    shutil.copy(OPENSPEC_LAUNCHER, plugin_bin / "openspec")
    (plugin_bin / "openspec").chmod(0o755)
    (fake / "npx").write_text(FAKE_NPX, encoding="utf-8", newline="\n")
    (fake / "npx").chmod(0o755)
    sh = shutil.which("sh")
    assert sh, "sh is not on PATH"
    path = os.pathsep.join([str(fake), str(plugin_bin), os.environ["PATH"]])
    result = subprocess.run(
        [sh, "-c", "openspec a 'b c'"],
        cwd=tmp_path,
        env={**os.environ, "PATH": path},
        capture_output=True,
        encoding="utf-8",
        check=False,
    )
    assert result.returncode == 3, result.stderr
    assert result.stdout == f"[-y][@fission-ai/openspec@{load_init().OPENSPEC}][a][b c]"


def test_openspec_pin_has_one_copy() -> None:
    """Scenario: One pin — outside `openspec/changes/`, only `bin/openspec` writes the version."""
    tracked = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, capture_output=True, encoding="utf-8", check=True
    ).stdout.splitlines()
    found = {}
    for name in tracked:
        if name.startswith("openspec/changes/"):
            continue
        try:
            text = (ROOT / name).read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if versions := OPENSPEC_PIN.findall(text):
            found[name] = versions
    assert found == {"bin/openspec": [load_init().OPENSPEC]}, found


def test_launcher_prefers_the_checkout_scripts(tmp_path: Path) -> None:
    """Scenario: Publisher checkout runs its own scripts."""
    checkout = tmp_path / "checkout"
    scripts = checkout / "skills" / "agent-process" / "scripts"
    scripts.mkdir(parents=True)
    (scripts / "probe.py").write_text(PROBE.format(where="checkout"), encoding="utf-8")
    result = _run_launcher(tmp_path, checkout, "probe x")
    assert result.returncode == 3, result.stderr
    assert result.stdout.strip() == "checkout ['x']"


def test_launcher_refuses_an_unknown_script(tmp_path: Path) -> None:
    """Scenario: Unknown script."""
    for args in ("", "nope", "../probe"):
        result = _run_launcher(tmp_path, tmp_path / "consumer", args)
        assert result.returncode == 2, (args, result.stdout, result.stderr)
        assert "probe" in result.stdout + result.stderr
        assert "plugin [" not in result.stdout


def test_launcher_runs_the_session_interpreter(tmp_path: Path) -> None:
    """Scenario: Launcher uses the session interpreter."""
    interpreter = tmp_path / "session-python"
    interpreter.write_text('#!/bin/sh\necho session "$@"\n', encoding="utf-8")
    interpreter.chmod(0o755)
    env = {"AGENT_PROCESS_PYTHON": interpreter.as_posix()}
    result = _run_launcher(tmp_path, tmp_path / "consumer", "probe a", env)
    assert result.returncode == 0, result.stderr
    word, script, arg = result.stdout.split()
    assert (word, arg) == ("session", "a"), result.stdout
    assert script.endswith("skills/agent-process/scripts/probe.py"), result.stdout


PLUGIN_HOOKS = ROOT / "hooks" / "hooks.json"
ADOPTION_MARKER = Path(".github") / "workflows" / "agent-process.yml"


def _plugin_hooks() -> list[tuple[str, str, str]]:
    """The `(event, matcher, command)` of every hook the plugin declares, read through the
    `"hooks"` envelope the platform requires of `hooks/hooks.json`."""
    return [
        (event, group.get("matcher", ""), hook["command"])
        for event, groups in _json(PLUGIN_HOOKS)["hooks"].items()
        for group in groups
        for hook in group["hooks"]
    ]


def _run_plugin_hook(
    project: Path, command: str, payload: dict, extra: dict[str, str | None] | None = None
) -> subprocess.CompletedProcess:
    """Run a hook command as the platform does: `sh -c`, the plugin root and project exported;
    `extra` sets variables, or removes the ones it maps to None."""
    sh = shutil.which("sh")
    assert sh, "sh is not on PATH"
    merged: dict[str, str | None] = {
        **os.environ,
        "CLAUDE_PROJECT_DIR": project.as_posix(),
        "CLAUDE_PLUGIN_ROOT": ROOT.as_posix(),
        **(extra or {}),
    }
    env = {name: value for name, value in merged.items() if value is not None}
    return subprocess.run(
        [sh, "-c", command],
        cwd=project,
        env=env,
        input=json.dumps(payload),
        capture_output=True,
        encoding="utf-8",
        check=False,
    )


def _denied_payloads(project: Path) -> dict[str, dict]:
    """Per matcher, a payload the navigation policy denies inside `project`."""
    large = project / "large.txt"
    large.write_text(("x" * 79 + "\n") * 1000, encoding="utf-8")  # 80000 bytes, over budget
    return {
        "Bash": {"tool_input": {"command": "cat README.md"}},
        "Read": {"tool_input": {"file_path": large.as_posix()}},
    }


def _memory_write(project: Path, separator: str = "/") -> dict:
    """A `Write` payload under the auto-memory directory, its path joined with `separator`."""
    parts = [project.as_posix(), ".claude", "projects", "slug", "memory", "fact.md"]
    return {"tool_name": "Write", "tool_input": {"file_path": separator.join(parts)}}


def _flagged_payloads(project: Path) -> dict[str, dict]:
    """Per matcher, a payload some plugin hook acts on inside an adopted `project`."""
    return {**_denied_payloads(project), "Edit|Write": _memory_write(project)}


def test_plugin_hooks_remind_on_memory_write_in_an_adopted_repository(tmp_path: Path) -> None:
    """Scenario: Memory write in an adopted consumer — the plugin's PostToolUse hook reminds."""
    (tmp_path / ADOPTION_MARKER).parent.mkdir(parents=True)
    (tmp_path / ADOPTION_MARKER).write_text("", encoding="utf-8")
    hooks = [
        command
        for event, matcher, command in _plugin_hooks()
        if (event, matcher) == ("PostToolUse", "Edit|Write") and "memory_checkpoint" in command
    ]
    assert len(hooks) == 1, _plugin_hooks()
    for separator in ("/", "\\"):
        payload = _memory_write(tmp_path, separator)
        result = _run_plugin_hook(tmp_path, hooks[0], payload)
        assert result.returncode == 2, (separator, result.stderr)
        assert payload["tool_input"]["file_path"] in result.stderr
        assert "repository" in result.stderr


def test_plugin_hooks_lint_the_edited_file_in_an_adopted_repository(tmp_path: Path) -> None:
    """Scenarios: Commit-stage finding, Lint error — the plugin's PostToolUse hook runs the
    project's `pre-commit`-stage hooks on the edited file and shows the finding."""
    repo = lint_repo(tmp_path / "repo", FINDING)
    (repo / ADOPTION_MARKER).parent.mkdir(parents=True)
    (repo / ADOPTION_MARKER).write_text("", encoding="utf-8")
    groups = _json(PLUGIN_HOOKS)["hooks"]["PostToolUse"]
    lint = [
        (group, hook)
        for group in groups
        for hook in group["hooks"]
        if "edit_lint" in hook["command"]
    ]
    assert len(lint) == 1, groups
    group, hook = lint[0]
    assert group["matcher"] == "Edit|Write"
    assert any("memory_checkpoint" in other["command"] for other in group["hooks"])
    assert hook["timeout"] == 120
    result = _run_plugin_hook(repo, hook["command"], edit_payload(repo / "a.py"))
    assert result.returncode == 2, result.stderr
    assert "finding:" in result.stderr


def test_plugin_hooks_deny_navigation_in_an_adopted_repository(tmp_path: Path) -> None:
    """Scenario: Adopted consumer — the marker and no copy of the policy; the plugin denies."""
    (tmp_path / ADOPTION_MARKER).parent.mkdir(parents=True)
    (tmp_path / ADOPTION_MARKER).write_text("", encoding="utf-8")
    payloads = _denied_payloads(tmp_path)
    hooks = [(matcher, command) for _, matcher, command in _plugin_hooks()]
    assert sorted(matcher for matcher, _ in hooks if matcher in payloads) == ["Bash", "Read"]
    replacement = {"Bash": "Read", "Read": "offset"}
    for matcher, command in hooks:
        if matcher not in payloads:
            continue
        result = _run_plugin_hook(tmp_path, command, payloads[matcher])
        assert result.returncode == 0, (matcher, result.stderr)
        output = json.loads(result.stdout)["hookSpecificOutput"]
        assert output["permissionDecision"] == "deny", matcher
        assert replacement[matcher] in output["permissionDecisionReason"], matcher


def test_plugin_hooks_are_silent_outside_an_adopted_repository(tmp_path: Path) -> None:
    """Scenario: Unadopted repository — every tool hook command exits 0 with no output."""
    payloads = _flagged_payloads(tmp_path)
    hooks = [hook for hook in _plugin_hooks() if hook[0] in {"PreToolUse", "PostToolUse"}]
    pre_tool_use = sorted(m for event, m, _ in hooks if event == "PreToolUse")
    assert {"Bash", "Read"} <= set(pre_tool_use), pre_tool_use
    for event, matcher, command in hooks:
        result = _run_plugin_hook(tmp_path, command, payloads.get(matcher, payloads["Bash"]))
        assert (result.returncode, result.stdout) == (0, ""), (event, matcher, result.stderr)


ENV_MARKER = "agent-process plugin environment not installed"


def _session_start(
    tmp_path: Path, manifest: str, **extra: str | None
) -> tuple[subprocess.CompletedProcess, Path | None]:
    """Run the plugin's one `SessionStart` command with a plugin root whose runtime manifest is
    `manifest`, the data directory `tmp_path/data` and a fresh env file; return the result and
    the interpreter the env file exports, if any."""
    hooks = [
        hook
        for group in _json(PLUGIN_HOOKS)["hooks"].get("SessionStart", [])
        for hook in group["hooks"]
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
    result = _run_plugin_hook(project, hooks[0]["command"], payload, variables)
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


def test_publisher_settings_declare_no_navigation_hook() -> None:
    """Scenario: Repository settings carry no navigation hook — the plugin delivers it."""
    groups = _json(SETTINGS).get("hooks", {}).get("PreToolUse", [])
    assert not [group for group in groups if group.get("matcher") in {"Bash", "Read"}]


def test_launcher_is_executable_in_git() -> None:
    staged = subprocess.run(
        ["git", "ls-files", "-s", "bin/agent-process"],
        cwd=ROOT,
        capture_output=True,
        encoding="utf-8",
        check=True,
    ).stdout
    assert staged.startswith("100755 "), staged


def test_marketplace_follows_stable() -> None:
    """Scenario: Channel render — every release declares the `stable` ref with auto-update."""
    init = load_init()
    for version in (init.VERSION, "0.0.1"):
        entry = init._render_settings(version)["extraKnownMarketplaces"][
            "agent-process-marketplace"
        ]
        assert entry["source"]["ref"] == "stable"
        assert entry["autoUpdate"] is True


def test_version_drift() -> None:
    release = _json(ROOT / ".release-please-manifest.json")["."]
    assert _json(PLUGIN)["version"] == release
    assert _json(MARKETPLACE)["plugins"][0]["version"] == release
    version_line = re.search(
        r"^VERSION = .*$", (SCRIPTS / "init.py").read_text(encoding="utf-8"), re.M
    )
    assert version_line is not None
    assert version_line.group(0) == f'VERSION = "{release}"  # x-release-please-version'
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert pyproject["project"]["version"] == release
    extra_files = _json(ROOT / "release-please-config.json")["packages"]["."]["extra-files"]
    assert sorted(extra_files, key=lambda place: place["path"]) == [
        {
            "type": "json",
            "path": ".claude-plugin/marketplace.json",
            "jsonpath": "$.plugins[0].version",
        },
        {"type": "json", "path": ".claude-plugin/plugin.json", "jsonpath": "$.version"},
        {"type": "toml", "path": "pyproject.toml", "jsonpath": "$.project.version"},
        {"type": "generic", "path": "skills/agent-process/scripts/init.py"},
    ]


def test_publisher_pre_push_runs_the_entry() -> None:
    """Scenario: This repository's push — its own checkout's `quality.py --hook` runs at
    `pre-push` in the pusher's environment (design D7)."""
    config = yaml.safe_load((ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8"))
    assert config["default_install_hook_types"] == ["pre-push"]
    assert [repo for repo in config["repos"] if repo["repo"] == "local"] == [
        {
            "repo": "local",
            "hooks": [
                {
                    "id": "quality",
                    "name": "quality",
                    "entry": "python skills/agent-process/scripts/quality.py --hook",
                    "language": "unsupported",
                    "stages": ["pre-push"],
                    "always_run": True,
                    "pass_filenames": False,
                }
            ],
        }
    ]


def test_publisher_lints_at_edit_time() -> None:
    """Scenarios: This repository's edit-time lint, Repository hook carries no memory check —
    ruff is declared once, by its published hooks at the `pre-commit` stage, and the
    repository's settings declare no post-edit hook of their own."""
    config = yaml.safe_load((ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8"))
    ruff = [
        r for r in config["repos"] if r["repo"] == "https://github.com/astral-sh/ruff-pre-commit"
    ]
    assert len(ruff) == 1, config["repos"]
    assert [(hook["id"], hook["stages"]) for hook in ruff[0]["hooks"]] == [
        ("ruff-check", ["pre-commit"]),
        ("ruff-format", ["pre-commit"]),
    ]
    requirements = (ROOT / ".agent-process" / "requirements-dev.in").read_text(encoding="utf-8")
    assert not [line for line in requirements.splitlines() if re.match(r"ruff\b", line)]
    assert "PostToolUse" not in _json(SETTINGS).get("hooks", {})
