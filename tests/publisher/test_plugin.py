"""The v2.0 plugin, shared skill, and closed consumer footprint."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / ".claude-plugin" / "plugin.json"
MARKETPLACE = ROOT / ".claude-plugin" / "marketplace.json"
SKILL = ROOT / "skills" / "agent-process" / "SKILL.md"
SCRIPTS = ROOT / "skills" / "agent-process" / "scripts"
TEMPLATES = ROOT / "skills" / "agent-process" / "templates"
MOVED_SCRIPTS = {
    "archive_change.py", "check_red.py", "create_tracking_issue.py",
    "resolve_review_thread.py", "set_status.py", "start_change.py", "wait_for_pr.py",
}
TEMPLATE_NAMES = {
    "agent-process.yml", "dependabot.yml", "config.yaml", "settings.json", "ruleset.json",
}


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_rule_change() -> None:
    config = yaml.safe_load((ROOT / "openspec" / "config.yaml").read_text(encoding="utf-8"))
    assert config["schema"] == "spec-driven"
    assert "This repository publishes" in config["context"]
    assert set(config["rules"]) == {"proposal", "specs", "design", "tasks"}
    for artifact, rules in config["rules"].items():
        joined = " ".join(rules)
        assert "skills/agent-process/SKILL.md" in joined
        assert f"#{artifact}" in joined
        assert len(joined) < 240


def test_shared_skill_owns_the_procedure_and_scripts() -> None:
    text = SKILL.read_text(encoding="utf-8")
    assert text.startswith("---\nname: agent-process\n")
    for heading in ("## Proposal", "## Specs", "## Design", "## Tasks", "## Architect review", "## Install"):
        assert heading in text
    assert {p.name for p in SCRIPTS.glob("*.py")} == MOVED_SCRIPTS | {"init.py"}
    for path in SCRIPTS.glob("*.py"):
        script = path.read_text(encoding="utf-8")
        assert "from scripts." not in script
        assert ".agent-process/scripts" not in script


def test_no_hooks() -> None:
    assert not (ROOT / "hooks").exists()
    assert "hooks" not in _json(PLUGIN)
    assert "hooks" not in _json(TEMPLATES / "settings.json")
    assert not any("hook" in p.name.lower() for p in TEMPLATES.rglob("*"))


def test_closed_installed_payload() -> None:
    assert {p.name for p in TEMPLATES.iterdir() if p.is_file()} == TEMPLATE_NAMES
    joined = "\n".join(p.read_text(encoding="utf-8") for p in TEMPLATES.iterdir())
    for forbidden in ("AGENTS.md", ".agent-process/", "REPORT_PATH", "REVIEW_CONTRACT.md"):
        assert forbidden not in joined


def test_publisher_dogfoods_process() -> None:
    caller = ROOT / ".github" / "workflows" / "agent-process.yml"
    assert caller.is_file()
    assert not (ROOT / ".github" / "workflows" / "ci.yml").exists()
    assert "skills/agent-process/SKILL.md" in (ROOT / "openspec" / "config.yaml").read_text(encoding="utf-8")


def test_settings_template_contains_only_portable_plugin_keys() -> None:
    assert set(_json(TEMPLATES / "settings.json")) == {"extraKnownMarketplaces", "enabledPlugins"}


def test_attribution_record_is_removed() -> None:
    assert not (ROOT / ".agent-process" / "copier-answers.yml").exists()


def test_version_drift() -> None:
    plugin = _json(PLUGIN)
    marketplace = _json(MARKETPLACE)
    assert plugin["version"] == "2.0.0"
    assert marketplace["plugins"][0]["version"] == plugin["version"]
    template = (TEMPLATES / "agent-process.yml").read_text(encoding="utf-8")
    assert "reusable-quality.yml@v2.0.0" in template
    init_source = (SCRIPTS / "init.py").read_text(encoding="utf-8")
    assert 'VERSION = "2.0.0"' in init_source

