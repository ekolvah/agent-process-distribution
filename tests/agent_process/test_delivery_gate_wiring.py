"""Repository-only v1 hook wiring retained during the v2 delivery transition.

The portable plugin has no hooks; its absence is covered by
``tests/publisher/test_plugin.py``. These assertions cover only this publisher's
temporary local settings until the remaining v1 cleanup changes land.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]


def test_publisher_claude_stop_hook_is_wired_once() -> None:
    settings = json.loads((_REPO / ".claude" / "settings.json").read_text(encoding="utf-8"))
    entries = settings["hooks"]["Stop"]
    assert len(entries) == 1
    commands = [hook["command"] for hook in entries[0]["hooks"]]
    assert any(re.search(r"hooks\.py stop", command) for command in commands)


def test_publisher_codex_hooks_remain_during_transition() -> None:
    hooks = json.loads((_REPO / ".codex" / "hooks.json").read_text(encoding="utf-8"))["hooks"]
    expected = {"PreToolUse": "pre-tool", "PostToolUse": "on-edit", "Stop": "stop"}
    for event, subcommand in expected.items():
        commands = [hook["command"] for entry in hooks[event] for hook in entry["hooks"]]
        assert any(re.search(rf"codex_hooks\.py {subcommand}", command) for command in commands)


def test_copier_attribution_record_is_not_a_contract() -> None:
    assert not (_REPO / ".agent-process" / "copier-answers.yml").exists()
