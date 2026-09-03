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


def _settings() -> Any:
    return json.loads(_CLAUDE_SETTINGS.read_text(encoding="utf-8"))


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
