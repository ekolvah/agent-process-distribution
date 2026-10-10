"""The navigation policy's read budget and its Claude PreToolUse adapter.

The policy applies to the byte size of the slice `Read` will actually return, and its
denial names the cheaper slice or search.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from tests.publisher.delivery_fakes import ROOT, SKILL_SCRIPTS, load_script

_policy = load_script("navigation_policy")
_READ_BUDGET_BYTES = _policy._READ_BUDGET_BYTES
read_budget_hint = _policy.read_budget_hint
pre_read_response = _policy.pre_read_response

_CLAUDE_SETTINGS = ROOT / ".claude" / "settings.json"


def _settings() -> Any:
    """The parsed settings file; shape is asserted by the tests that read it."""
    return json.loads(_CLAUDE_SETTINGS.read_text(encoding="utf-8"))


def _text_file(tmp_path: Path, name: str, size: int) -> Path:
    """A UTF-8 file of at least `size` bytes, in 40-byte lines so slices are addressable."""
    line = "x" * 39 + "\n"
    path = tmp_path / name
    path.write_text(line * (size // len(line) + 1), encoding="utf-8")
    return path


def _over_budget(tmp_path: Path, name: str = "big.py") -> Path:
    return _text_file(tmp_path, name, _READ_BUDGET_BYTES * 2)


def _not_a_string(_: Path) -> object:
    return 12


def _missing(tmp_path: Path) -> str:
    return str(tmp_path / "gone.py")


def _a_directory(tmp_path: Path) -> str:
    return str(tmp_path)


def _undecodable(tmp_path: Path) -> str:
    path = tmp_path / "blob.bin"
    path.write_bytes(b"\xff\xfe\x00\x01" * _READ_BUDGET_BYTES)
    return str(path)


def _asset(suffix: str) -> Callable[[Path], str]:
    """A file large enough to bust the budget, in a format where offset/limit make no sense."""

    def make(tmp_path: Path) -> str:
        return str(_over_budget(tmp_path, f"asset{suffix}"))

    return make


class TestReadBudget:
    """`Read` is the other route into the filesystem, and the one left ungated."""

    def test_whole_file_read_over_threshold_is_denied(self, tmp_path: Path) -> None:
        hint = read_budget_hint(str(_over_budget(tmp_path)))
        assert hint is not None
        assert "Grep" in hint
        assert "offset" in hint
        # The concrete slice that fits, not a task to guess it.
        assert re.search(r"limit=\d+", hint), hint

    def test_denial_states_the_measured_cost(self, tmp_path: Path) -> None:
        """§IV: the price is on screen when the decision is made, not implied."""
        path = _over_budget(tmp_path, "big.md")
        hint = read_budget_hint(str(path))
        assert hint is not None
        assert str(path.stat().st_size) in hint
        assert "token" in hint

    def test_denial_names_the_whole_file_rewrite_hazard(self, tmp_path: Path) -> None:
        """Slicing a file the agent is about to rewrite must not turn into data loss."""
        hint = read_budget_hint(str(_over_budget(tmp_path)))
        assert hint is not None
        assert "Write" in hint

    def test_file_below_threshold_is_allowed_whole(self, tmp_path: Path) -> None:
        path = _text_file(tmp_path, "small.py", _READ_BUDGET_BYTES // 4)
        assert read_budget_hint(str(path)) is None

    def test_slice_within_budget_is_allowed_on_a_large_file(self, tmp_path: Path) -> None:
        path = _text_file(tmp_path, "huge.py", _READ_BUDGET_BYTES * 4)
        assert read_budget_hint(str(path), offset=1, limit=50) is None

    def test_default_line_limit_on_a_large_file_is_still_denied(self, tmp_path: Path) -> None:
        """`limit` counts LINES and `Read` truncates at 2000 of them; the longest file in
        this repository is 1196 lines, so `limit=2000` returns the whole file. A rule keyed
        on "is `limit` present" would have been a rename, not a policy."""
        assert read_budget_hint(str(_over_budget(tmp_path)), limit=2000) is not None

    @pytest.mark.parametrize(
        "make_path",
        (
            _not_a_string,
            _missing,
            _a_directory,
            _undecodable,
            *map(_asset, (".pdf", ".ipynb", ".png")),
        ),
        ids=("non-string", "missing", "directory", "undecodable", "pdf", "ipynb", "png"),
    )
    def test_fails_open(self, tmp_path: Path, make_path: Callable[[Path], object]) -> None:
        """The policy claims only that a cheaper route exists, so anything it cannot measure
        is "no opinion" — never a block."""
        assert read_budget_hint(make_path(tmp_path)) is None

    def test_fails_open_on_non_integer_slice_arguments(self, tmp_path: Path) -> None:
        """A payload whose `offset`/`limit` cannot be read as line counts is unmeasurable."""
        path = _over_budget(tmp_path)
        assert read_budget_hint(str(path), offset="1", limit="50") is None


class TestClaudeAdapter:
    def test_read_denial_uses_the_documented_pretooluse_shape(self, tmp_path: Path) -> None:
        response = pre_read_response({"tool_input": {"file_path": str(_over_budget(tmp_path))}})
        assert response is not None
        specific = response["hookSpecificOutput"]
        assert specific["hookEventName"] == "PreToolUse"
        assert specific["permissionDecision"] == "deny"
        assert "Grep" in specific["permissionDecisionReason"]

    def test_read_allowed_call_and_malformed_payload_return_no_decision(
        self, tmp_path: Path
    ) -> None:
        small = _text_file(tmp_path, "small.py", 500)
        assert pre_read_response({"tool_input": {"file_path": str(small)}}) is None
        assert pre_read_response({}) is None
        assert pre_read_response({"tool_input": {"file_path": None}}) is None


@pytest.mark.parametrize("args", ((), ("pre-bash",)))
def test_unknown_subcommand_is_a_visible_non_blocking_error(args: tuple[str, ...]) -> None:
    """Exit 2 behind a `Bash` matcher would deny every call; exit 1 is a visible hook error."""
    result = subprocess.run(
        [sys.executable, str(SKILL_SCRIPTS / "navigation_policy.py"), *args],
        input="{}",
        capture_output=True,
        encoding="utf-8",
        check=False,
    )
    assert result.returncode == 1
    assert "usage" in result.stderr


def test_pre_read_subcommand_is_accepted() -> None:
    """The hook's own subcommand reaches the policy: an empty payload is no decision."""
    result = subprocess.run(
        [sys.executable, str(SKILL_SCRIPTS / "navigation_policy.py"), "pre-read"],
        input="{}",
        capture_output=True,
        encoding="utf-8",
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == ""


class TestClaudeHookWiring:
    def test_no_static_deny_shadows_the_read_hook(self) -> None:
        """A `Read(...)` deny rule would block before the hook runs and drop the budget
        message, leaving the agent with a refusal and no cheaper route named."""
        patterns = [str(p) for p in _settings()["permissions"]["deny"]]
        shadowing = [pattern for pattern in patterns if re.match(r"Read\(", pattern)]
        assert not shadowing, f"static deny entries shadow the read hook: {shadowing}"
