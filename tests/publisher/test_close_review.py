"""The review job's closing comment: the marker, the session's final message, its denials."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import close_review, head_review

_HEAD = "a" * 40
_OTHER = "b" * 40
_TEXT = (
    "Read the contract, the diff and design D2.\n\n"
    f"No findings. Not verified: git_guard. Reviewed head SHA: {_OTHER}"
)


def _result(text: str, denials: list[dict[str, object]] | None = None) -> dict[str, object]:
    return {
        "type": "result",
        "subtype": "success",
        "is_error": False,
        "result": text,
        "permission_denials": denials or [],
    }


def _denial(tool: str, tool_input: dict[str, object]) -> dict[str, object]:
    return {"tool_name": tool, "tool_use_id": "toolu_1", "tool_input": tool_input}


def _close(tmp_path: Path, messages: object) -> Path:
    execution = tmp_path / "claude-execution-output.json"
    execution.write_text(json.dumps(messages), encoding="utf-8")
    body = tmp_path / "review-close.md"
    close_review.main(
        ["--execution-file", str(execution), "--head-sha", _HEAD, "--body-file", str(body)]
    )
    return body


def test_body_carries_marker_message_and_denials(tmp_path: Path) -> None:
    """Scenarios: New head, Denied tool — the marker comes first, so a marker the model wrote
    in its text never shadows it."""
    command = "gh api user ."
    messages = [
        {"type": "system", "subtype": "init"},
        _result(_TEXT, [_denial("Bash", {"command": command, "description": "who"})]),
    ]

    body = _close(tmp_path, messages).read_text(encoding="utf-8")

    assert body.splitlines()[0] == f"Reviewed head SHA: {_HEAD}"
    assert _TEXT in body
    assert "Permission denials: 1" in body
    assert json.dumps(command) in body
    comment = {"author": {"login": "github-actions[bot]"}, "body": body}
    assert head_review.reviewed({"comments": {"nodes": [comment]}}, _HEAD)


def test_denial_without_command_renders_its_input(tmp_path: Path) -> None:
    """Scenario: Denied tool — a denied call without a command shows its input."""
    denial = _denial("Read", {"file_path": "/home/runner/.ssh/id_rsa"})

    body = _close(tmp_path, [_result(_TEXT, [denial])]).read_text(encoding="utf-8")

    assert "Permission denials: 1" in body
    assert "Read" in body
    assert "/home/runner/.ssh/id_rsa" in body


def test_multiline_denial_stays_on_one_line(tmp_path: Path) -> None:
    """Scenario: Denied tool — a multi-line command stays on its own line."""
    heredoc = "cat > x <<EOF\nline one\nline two\nEOF"
    without = _close(tmp_path, [_result(_TEXT)]).read_text(encoding="utf-8")

    body = _close(tmp_path, [_result(_TEXT, [_denial("Bash", {"command": heredoc})])]).read_text(
        encoding="utf-8"
    )

    assert len(body.splitlines()) == len(without.splitlines()) + 1
    assert json.dumps(heredoc) in body


@pytest.mark.parametrize(
    "messages",
    [None, {"type": "result", "result": _TEXT}, [{"type": "system"}], [_result(" \n")]],
    ids=["missing", "not-a-list", "no-result", "blank-result"],
)
def test_silent_finish_writes_no_body(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], messages: object
) -> None:
    """Scenario: Silent finish — no final message, no closing comment, a failed check."""
    execution = tmp_path / "claude-execution-output.json"
    if messages is not None:
        execution.write_text(json.dumps(messages), encoding="utf-8")
    body = tmp_path / "review-close.md"

    with pytest.raises(SystemExit) as exit_info:
        close_review.main(
            ["--execution-file", str(execution), "--head-sha", _HEAD, "--body-file", str(body)]
        )

    assert exit_info.value.code == 1
    assert "::error::" in capsys.readouterr().out
    assert not body.exists()
