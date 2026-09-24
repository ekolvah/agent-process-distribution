"""The shared package boundary: the procedure, its scripts, and the installer's templates."""

from __future__ import annotations

import json
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
        {"SKILL.md", "architect-review.schema.json"}
        | {f"scripts/{name}" for name in MOVED_SCRIPTS}
        | {f"templates/{name}" for name in TEMPLATES}
    )
    forbidden = ("hook",)
    assert not any(token in path.lower() for path in relative_files for token in forbidden)


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
    config = yaml.safe_load((ROOT / "openspec" / "config.yaml").read_text(encoding="utf-8"))
    assert all(
        "skills/agent-process/SKILL.md" in " ".join(rule) for rule in config["rules"].values()
    )


def test_version_drift() -> None:
    plugin = _json(PLUGIN)
    marketplace = _json(MARKETPLACE)
    assert plugin["version"] == "2.0.0"
    assert marketplace["plugins"][0]["version"] == plugin["version"]
