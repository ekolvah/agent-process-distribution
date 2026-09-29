"""The shared package boundary: the procedure, its scripts, and the installer's templates."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
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
    roots = (PACKAGE, ROOT / "agents", ROOT / "commands")
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


COMPONENT_ROOTS = [".claude-plugin", "agents", "bin", "commands", "skills/agent-process"]
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
    extra_files = _json(ROOT / "release-please-config.json")["packages"]["."]["extra-files"]
    assert sorted(extra_files, key=lambda place: place["path"]) == [
        {
            "type": "json",
            "path": ".claude-plugin/marketplace.json",
            "jsonpath": "$.plugins[0].version",
        },
        {"type": "json", "path": ".claude-plugin/plugin.json", "jsonpath": "$.version"},
        {"type": "generic", "path": "skills/agent-process/scripts/init.py"},
    ]
