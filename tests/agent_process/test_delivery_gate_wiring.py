"""The hook wiring of `.claude/settings.json` and `.codex/hooks.json`.

The turn-boundary `Stop` gate was removed (change v2-4a-review-protection, design D2), so
neither adapter wires a `Stop` event. The hooks' logic is covered in
`tests/publisher/test_hooks.py` and `tests/publisher/test_codex_hooks.py`.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[2]
_CLAUDE_SETTINGS = _REPO / ".claude" / "settings.json"
_CODEX_HOOKS = _REPO / ".codex" / "hooks.json"


def _settings() -> Any:
    return json.loads(_CLAUDE_SETTINGS.read_text(encoding="utf-8"))


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


def test_claude_wires_no_stop_hook() -> None:
    assert "Stop" not in _settings()["hooks"]


class TestTelemetryAttribution:
    """Project attribution on the agent telemetry (issue #97).

    A telemetry assertion in a file whose stated subject is hook and gate wiring is
    deliberate: this is the one place that already reads `.claude/settings.json`,
    and the attribution rides the same file.

    Deliberate gap, recorded here rather than reopened as work-for-work: no test
    asserts that a *live* Claude Code session emits these attributes. That crosses
    a process boundary into the harness and a third-party exporter; issue #97's
    AC1(a) covers it as a one-shot observation with captured evidence, following
    the convention in `tests/publisher/test_test_suite_ownership.py`.
    """

    def test_settings_carry_the_project_as_a_resource_attribute(self) -> None:
        project = _resource_attributes()["vcs.repository.name"]
        assert re.fullmatch(r"[^/\s]+/[^/\s]+", project), (
            f"the project attribute must be `<owner>/<repository>`: {project!r}"
        )

    def test_the_carrier_stays_a_multi_pair_list(self) -> None:
        attributes = _resource_attributes()

        project = attributes["vcs.repository.name"]
        assert attributes["vcs.repository.url.full"] == f"https://github.com/{project}"
        assert len(attributes) >= 2


class TestCodexHookWiring:
    """`.codex/hooks.json` is mandatory (issue #75, AC 6): a missing file fails
    loudly rather than skipping silently (§IV)."""

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

        assert "Stop" not in hooks
