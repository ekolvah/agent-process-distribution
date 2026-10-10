"""The review job's closing comment: the marker, the session's final message, its denials."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from markdown_it import MarkdownIt
from markdown_it.token import Token

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


_GITHUB_LIMIT = 65_536
_MEDIUMBLOB = 262_144
_TRUNCATED = " … truncated"


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


def _fences(body: str) -> list[Token]:
    return [t for t in MarkdownIt("commonmark").parse(body) if t.type == "fence"]


def test_multiline_denial_stays_on_one_line(tmp_path: Path) -> None:
    """Scenario: Denied tool — a multi-line command is the one line of the fenced block."""
    heredoc = "cat > x <<EOF\nline one\nline two\nEOF"

    body = _close(tmp_path, [_result(_TEXT, [_denial("Bash", {"command": heredoc})])]).read_text(
        encoding="utf-8"
    )

    fences = _fences(body)
    assert fences
    assert fences[0].content == f"- Bash: {json.dumps(heredoc)}\n"


@pytest.mark.parametrize("opener", ["<!--", "<details>", "```"])
def test_message_cannot_hide_the_denials(tmp_path: Path, opener: str) -> None:
    """Scenario: Denied tool — a block the final message opens and never closes hides
    nothing: the denials come before it, in a fence their own text cannot close."""
    command = "echo '```'\n<!--"
    denial = _denial("Bash", {"command": command})

    body = _close(tmp_path, [_result(f"{_TEXT}\n{opener}", [denial])]).read_text(encoding="utf-8")

    tokens = MarkdownIt("commonmark").parse(body)
    fences = [i for i, t in enumerate(tokens) if t.type == "fence"]
    assert fences
    assert tokens[fences[0]].content == f"- Bash: {json.dumps(command)}\n"
    count = [
        i
        for i, t in enumerate(tokens)
        if t.type == "inline" and t.content == "Permission denials: 1"
    ]
    html = [
        i
        for i, t in enumerate(tokens)
        if t.type == "html_block" or any(child.type == "html_inline" for child in t.children or [])
    ]
    assert count
    assert all(max(count[0], fences[0]) < i for i in html)


def test_oversized_denial_is_cut(tmp_path: Path) -> None:
    """Scenario: Oversized session — one denied call cannot fill the comment."""
    denial = _denial("Write", {"file_path": "a.py", "content": "x" * 100_000})

    body = _close(tmp_path, [_result(_TEXT, [denial])]).read_text(encoding="utf-8")

    lines = body.splitlines()
    assert len(body) <= _GITHUB_LIMIT
    assert "Permission denials: 1" in lines
    [line] = [line for line in lines if line.startswith("- Write: ")]
    assert line.endswith(_TRUNCATED)
    assert len(line) <= 1_000 + len(_TRUNCATED)


@pytest.mark.parametrize(
    ("text", "denials"),
    [
        ("x" * 100_000, 0),
        ("😀" * 100_000, 0),
        (_TEXT, 100),
    ],
    ids=["ascii-message", "emoji-message", "many-denials"],
)
def test_oversized_body_is_cut(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], text: str, denials: int
) -> None:
    """Scenario: Oversized session — the comment stays under GitHub's limit, the marker
    and the count stay whole, and the cut is marked on the PR and in the job log."""
    calls = [_denial("Bash", {"command": "y" * 5_000}) for _ in range(denials)]

    body = _close(tmp_path, [_result(text, calls)]).read_text(encoding="utf-8")

    lines = body.splitlines()
    assert len(body) <= _GITHUB_LIMIT
    assert len(body.encode("utf-8")) <= _MEDIUMBLOB
    assert lines[0] == f"Reviewed head SHA: {_HEAD}"
    assert f"Permission denials: {denials}" in lines
    assert lines[-1] == "… truncated"
    assert "::warning::" in capsys.readouterr().out


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
