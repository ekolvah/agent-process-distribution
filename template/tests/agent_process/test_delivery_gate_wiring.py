"""The delivery turn-boundary gate's Claude `Stop` wiring (issue #56).

The decision logic itself (`scripts.delivery_state`) and its adapter
(`scripts.hooks.stop_response`) are covered in `tests/publisher/test_hooks.py`
and `tests/publisher/test_delivery_state.py`; this file only asserts the
`.claude/settings.json` wiring, mirroring `TestClaudeHookWiring` in
`test_navigation_policy.py`.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest
import yaml

_REPO = Path(__file__).resolve().parents[2]
_CLAUDE_SETTINGS = _REPO / ".claude" / "settings.json"
_CODEX_HOOKS = _REPO / ".codex" / "hooks.json"
_COPIER_ANSWERS = _REPO / ".agent-process" / "copier-answers.yml"


def _settings() -> Any:
    return json.loads(_CLAUDE_SETTINGS.read_text(encoding="utf-8"))


def _answers() -> dict[str, Any]:
    return yaml.safe_load(_COPIER_ANSWERS.read_text(encoding="utf-8"))


def _resource_attributes() -> dict[str, str]:
    """Parse `OTEL_RESOURCE_ATTRIBUTES` the way the OTel SDK does: a comma-joined
    `key=value` list. Returning a mapping rather than the raw string is the point —
    the carrier has to stay a list so a later launch-time step can add a pair to it
    (issue #101) without rewriting the format."""
    raw = _settings()["env"]["OTEL_RESOURCE_ATTRIBUTES"]
    pairs = {}
    for part in raw.split(","):
        assert "=" in part, f"not a key=value pair: {part!r}"
        key, _, value = part.partition("=")
        pairs[key] = value
    return pairs


def _codex_hooks() -> Any:
    return json.loads(_CODEX_HOOKS.read_text(encoding="utf-8"))


@pytest.mark.skipif(
    not _CLAUDE_SETTINGS.is_file(),
    reason="the generated project does not include the optional Claude adapter",
)
class TestStopHookWiring:
    def test_stop_hook_is_wired_exactly_once(self) -> None:
        entries = _settings()["hooks"]["Stop"]
        assert len(entries) == 1
        commands = [hook["command"] for hook in entries[0]["hooks"]]
        assert any(re.search(r"hooks\.py stop", command) for command in commands)


@pytest.mark.skipif(
    not _CLAUDE_SETTINGS.is_file(),
    reason="the generated project does not include the optional Claude adapter",
)
class TestTelemetryAttribution:
    """Project attribution on the agent telemetry (issue #97).

    A telemetry assertion in a file whose stated subject is hook and gate wiring is
    deliberate: this is the one place that already reads `.claude/settings.json`
    behind the optional-adapter `skipif`, and the attribution rides the same file.

    Deliberate gap, recorded here rather than reopened as work-for-work: no test
    asserts that a *live* Claude Code session emits these attributes. That crosses
    a process boundary into the harness and a third-party exporter; issue #97's
    AC1(a) covers it as a one-shot observation with captured evidence, following
    the convention in `tests/publisher/test_test_suite_ownership.py` and
    `tests/agent_process/test_branch_protection.py`.
    """

    def test_settings_carry_the_project_as_a_resource_attribute(self) -> None:
        attributes = _resource_attributes()
        answers = _answers()

        project = attributes["vcs.repository.name"]
        assert project, "the project attribute must not be empty"
        # Which of the two answers wins is a template rule, tested once against the
        # real template in tests/publisher/test_project_bootstrap_template.py; this
        # copy only asserts the value is one of them and so cannot drift into a
        # second encoding of the fallback.
        assert project in {answers.get("github_repository"), answers.get("repo_name")}

    def test_the_carrier_stays_a_multi_pair_list(self) -> None:
        attributes = _resource_attributes()
        answers = _answers()

        github_repository = answers.get("github_repository")
        if github_repository:
            assert (
                attributes["vcs.repository.url.full"] == f"https://github.com/{github_repository}"
            )
            assert len(attributes) >= 2
        else:
            # An adopter who left `github_repository` blank has no canonical URL,
            # so the pair is omitted rather than guessed. `template_drift` and T2
            # cover the rendering rule itself.
            assert "vcs.repository.url.full" not in attributes


class TestCodexHookWiring:
    """`.codex/hooks.json` is mandatory in every render (issue #75, AC 6): unlike
    `TestStopHookWiring` above, this class takes no `skipif` — a missing file here
    must fail loudly, not skip silently (§IV)."""

    def test_every_event_group_maps_to_its_subcommand(self) -> None:
        hooks = _codex_hooks()["hooks"]

        pre_tool_use = hooks["PreToolUse"]
        assert len(pre_tool_use) == 1
        assert pre_tool_use[0]["matcher"] == "^Bash$"
        pre_tool_commands = [hook["command"] for hook in pre_tool_use[0]["hooks"]]
        assert any(re.search(r"codex_hooks\.py pre-tool", command) for command in pre_tool_commands)

        post_tool_use = hooks["PostToolUse"]
        assert len(post_tool_use) == 1
        assert post_tool_use[0]["matcher"] == "^apply_patch$"
        post_tool_commands = [hook["command"] for hook in post_tool_use[0]["hooks"]]
        assert any(re.search(r"codex_hooks\.py on-edit", command) for command in post_tool_commands)

        stop = hooks["Stop"]
        assert len(stop) == 1
        assert "matcher" not in stop[0]
        stop_commands = [hook["command"] for hook in stop[0]["hooks"]]
        assert any(re.search(r"codex_hooks\.py stop", command) for command in stop_commands)
