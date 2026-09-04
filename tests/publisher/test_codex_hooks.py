"""Unit tests for the Codex hook adapter and shared edit-feedback path."""

from __future__ import annotations

import io
import json
import subprocess
import sys
from pathlib import Path

import pytest

import scripts.codex_hooks as codex_hooks
from scripts.codex_hooks import edited_paths, pre_tool_response, read_payload, run_on_edit

_REPO = Path(__file__).resolve().parents[2]
_STOP_COMMAND_OUTPUT_KEYS = {
    "continue",
    "stopReason",
    "suppressOutput",
    "systemMessage",
    "decision",
    "reason",
}


def _patch(*paths: str) -> dict:
    command = "*** Begin Patch\n" + "".join(f"*** Update File: {path}\n" for path in paths)
    return {"tool_input": {"command": command}}


class TestPreToolUse:
    def test_forbidden_git_operation_uses_codex_denial_schema(self) -> None:
        response = pre_tool_response({"tool_input": {"command": "git push origin main"}})
        assert response == {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": "Blocked by repository policy: git push to main.",
            }
        }

    def test_safe_command_has_no_hook_response(self) -> None:
        assert (
            pre_tool_response({"tool_input": {"command": "python -m pytest tests/test_x.py"}})
            is None
        )

    def test_malformed_payload_fails_closed(self) -> None:
        result = subprocess.run(
            [sys.executable, ".agent-process/scripts/codex_hooks.py", "pre-tool"],
            cwd=_REPO,
            input="not json",
            text=True,
            capture_output=True,
            encoding="utf-8",
            check=False,
        )
        assert result.returncode == 2
        assert json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"] == "deny"

    def test_module_invocation_imports_shared_policy_from_repo_root(self) -> None:
        result = subprocess.run(
            [sys.executable, ".agent-process/scripts/codex_hooks.py", "pre-tool"],
            cwd=_REPO,
            input=json.dumps({"tool_input": {"command": "git push origin main"}}),
            text=True,
            capture_output=True,
            encoding="utf-8",
            check=False,
        )
        assert result.returncode == 0, result.stderr
        assert json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"] == "deny"


class TestPostToolUse:
    def test_apply_patch_paths_are_deduplicated_and_ignore_deletes(self) -> None:
        payload = {
            "tool_input": {
                "command": """*** Begin Patch
*** Add File: src/new.py
*** Update File: src/new.py
*** Update File: requirements.in
*** Delete File: src/old.py
*** End Patch"""
            }
        }
        assert edited_paths(payload) == ["src/new.py", "requirements.in"]

    def test_apply_patch_rename_checks_destination(self) -> None:
        payload = {
            "tool_input": {
                "command": "*** Begin Patch\n*** Move to: .agent-process/scripts/new_name.py\n*** End Patch"
            }
        }
        assert edited_paths(payload) == [".agent-process/scripts/new_name.py"]

    def test_python_edit_uses_shared_ruff_feedback(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(codex_hooks, "run_on_paths", lambda paths: (2, repr(paths)))
        assert run_on_edit(_patch("src/new.py", "requirements.in")) == (
            2,
            "['src/new.py', 'requirements.in']",
        )

    def test_malformed_payload_is_silent_noop(self) -> None:
        assert read_payload("not json") == {}
        assert run_on_edit({}) == (0, "")


class TestStopSubcommand:
    """`codex_hooks.py stop` (issue #75) delegates to `hooks.stop_response` — the shared
    decision is covered by `tests/publisher/test_delivery_state.py` and
    `tests/publisher/test_hooks.py::TestStopHook`; every node here drives `main()`, the
    code that is actually new, not a pass-through (§VII, plan `## Test plan`)."""

    def test_block_decision_reaches_stdout_and_exits_zero(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setattr(
            codex_hooks,
            "stop_response",
            lambda payload: {"decision": "block", "reason": "delivery not terminal"},
        )
        monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"hook_event_name": "Stop"})))
        codex_hooks.main(["stop"])
        captured = capsys.readouterr()
        assert json.loads(captured.out) == {
            "decision": "block",
            "reason": "delivery not terminal",
        }
        assert captured.err == ""

    def test_escalation_marker_reaches_stdout(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setattr(
            codex_hooks,
            "stop_response",
            lambda payload: {"systemMessage": "delivery not terminal after 5 consecutive blocks"},
        )
        monkeypatch.setattr(sys, "stdin", io.StringIO("{}"))
        codex_hooks.main(["stop"])
        captured = capsys.readouterr()
        assert json.loads(captured.out) == {
            "systemMessage": "delivery not terminal after 5 consecutive blocks"
        }

    def test_terminal_delivery_writes_nothing(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setattr(codex_hooks, "stop_response", lambda payload: None)
        monkeypatch.setattr(sys, "stdin", io.StringIO("{}"))
        codex_hooks.main(["stop"])
        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == ""

    def test_emitted_keys_stay_inside_stop_command_output(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        for response in (
            {"decision": "block", "reason": "delivery not terminal"},
            {"systemMessage": "delivery not terminal after 5 consecutive blocks"},
        ):
            monkeypatch.setattr(
                codex_hooks, "stop_response", lambda payload, response=response: response
            )
            monkeypatch.setattr(sys, "stdin", io.StringIO("{}"))
            codex_hooks.main(["stop"])
            captured = capsys.readouterr()
            assert set(json.loads(captured.out).keys()) <= _STOP_COMMAND_OUTPUT_KEYS

    def test_stop_does_not_fail_closed_on_a_malformed_payload(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        received: dict[str, object] = {}

        def fake_stop_response(payload: dict) -> None:
            received["payload"] = payload
            return None

        monkeypatch.setattr(codex_hooks, "stop_response", fake_stop_response)
        monkeypatch.setattr(sys, "stdin", io.StringIO("not json"))
        codex_hooks.main(["stop"])
        assert received["payload"] == {}
        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == ""

    def test_stop_end_to_end_from_a_non_git_directory(self, tmp_path: Path) -> None:
        # cwd=tmp_path, never cwd=_REPO: `hooks._write_budget` is the single writer of
        # `.agent_stop_blocks` in the process CWD, so running this at the repo root would
        # consume the live gate's own block budget -- including during this issue's own
        # delivery (architect finding S3).
        result = subprocess.run(
            [sys.executable, str(_REPO / ".agent-process" / "scripts" / "codex_hooks.py"), "stop"],
            cwd=tmp_path,
            input="{}",
            text=True,
            capture_output=True,
            encoding="utf-8",
            check=False,
        )
        assert result.returncode == 0, result.stderr
        response = json.loads(result.stdout)
        assert response["decision"] == "block"
