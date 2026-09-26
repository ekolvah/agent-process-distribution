"""The shared package boundary: the procedure, its scripts, and the installer's templates."""

from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

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
    "resolve_review_thread.py",
    "set_status.py",
    "start_change.py",
    "wait_for_pr.py",
}

TEMPLATES = {
    "agent-process.yml",
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
        # `~/.agent-process/` is the installer's user-profile checkout, not a repository path.
        findings += [
            f"{name}: {m.group()}" for m in re.finditer(r"(?<!~/)\.agent-process/\S*", text)
        ]
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
    assert settings["enabledPlugins"] == {"agent-process@agent-process-marketplace": True}
    commands = [
        hook["command"] for group in settings["hooks"]["SessionStart"] for hook in group["hooks"]
    ]
    assert any("skills/agent-process/templates/skill_check.py" in c for c in commands)
    config = yaml.safe_load((ROOT / "openspec" / "config.yaml").read_text(encoding="utf-8"))
    assert all(
        "skills/agent-process/SKILL.md" in " ".join(rule) for rule in config["rules"].values()
    )


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
