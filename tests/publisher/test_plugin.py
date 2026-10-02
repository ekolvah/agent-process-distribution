"""The shared package boundary: the procedure, its scripts, and the installer's templates."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tomllib
from pathlib import Path

import yaml

from tests.publisher.init_harness import load_init

ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / ".claude-plugin" / "plugin.json"
MARKETPLACE = ROOT / ".claude-plugin" / "marketplace.json"
SETTINGS = ROOT / ".claude" / "settings.json"
SKILL = ROOT / "skills" / "agent-process" / "SKILL.md"
PACKAGE = SKILL.parent
SCRIPTS = PACKAGE / "scripts"
MOVED_SCRIPTS = {
    "activate_protection.py",
    "archive_change.py",
    "check_red.py",
    "create_tracking_issue.py",
    "init.py",
    "manual.py",
    "memory_checkpoint.py",
    "navigation_policy.py",
    "onboarding.py",
    "quality.py",
    "resolve_review_thread.py",
    "set_status.py",
    "start_change.py",
    "steps.py",
    "wait_for_pr.py",
}

TEMPLATES = {
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


def _run_launcher(tmp_path: Path, cwd: Path, args: str) -> subprocess.CompletedProcess[str]:
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
    env = {**os.environ, "PATH": os.pathsep.join([str(plugin / "bin"), os.environ["PATH"]])}
    cwd.mkdir(parents=True, exist_ok=True)
    return subprocess.run(
        [sh, "-c", f"agent-process {args}"],
        cwd=cwd,
        env=env,
        capture_output=True,
        encoding="utf-8",
        check=False,
    )


def test_launcher_runs_the_plugin_script_from_a_consumer(tmp_path: Path) -> None:
    """Scenario: Printed command in a consumer."""
    result = _run_launcher(tmp_path, tmp_path / "consumer", "probe a 'b c'")
    assert result.returncode == 3, result.stderr
    assert result.stdout.strip() == "plugin ['a', 'b c']"


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


def _run_plugin_hook(project: Path, command: str, payload: dict) -> subprocess.CompletedProcess:
    """Run a hook command as the platform does: `sh -c`, the plugin root and project exported."""
    sh = shutil.which("sh")
    assert sh, "sh is not on PATH"
    env = {
        **os.environ,
        "CLAUDE_PROJECT_DIR": project.as_posix(),
        "CLAUDE_PLUGIN_ROOT": ROOT.as_posix(),
    }
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
        if (event, matcher) == ("PostToolUse", "Edit|Write")
    ]
    assert len(hooks) == 1, _plugin_hooks()
    for separator in ("/", "\\"):
        payload = _memory_write(tmp_path, separator)
        result = _run_plugin_hook(tmp_path, hooks[0], payload)
        assert result.returncode == 2, (separator, result.stderr)
        assert payload["tool_input"]["file_path"] in result.stderr
        assert "repository" in result.stderr


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
    """Scenario: Unadopted repository — every plugin hook command exits 0 with no output."""
    payloads = _flagged_payloads(tmp_path)
    hooks = _plugin_hooks()
    pre_tool_use = sorted(m for event, m, _ in hooks if event == "PreToolUse")
    assert {"Bash", "Read"} <= set(pre_tool_use), pre_tool_use
    for event, matcher, command in hooks:
        result = _run_plugin_hook(tmp_path, command, payloads.get(matcher, payloads["Bash"]))
        assert (result.returncode, result.stdout) == (0, ""), (event, matcher, result.stderr)


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
    assert config["repos"] == [
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
