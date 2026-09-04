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

_REPO = Path(__file__).resolve().parents[2]
_CLAUDE_SETTINGS = _REPO / ".claude" / "settings.json"
_CODEX_HOOKS = _REPO / ".codex" / "hooks.json"


def _settings() -> Any:
    return json.loads(_CLAUDE_SETTINGS.read_text(encoding="utf-8"))


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
