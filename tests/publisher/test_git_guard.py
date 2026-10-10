"""The git guard: the plugin's `PreToolUse` `Bash` stop for merge and irreversible git commands.

Driven through the CLI only, as the platform runs it: the payload on stdin, the decision on
stdout. It replaces this repository's static `permissions.deny` block, which a plugin cannot ship
and which names no alternative.
"""

from __future__ import annotations

import json
import re
import shlex
import subprocess
import sys

import pytest

from tests.publisher.delivery_fakes import ROOT, SKILL_SCRIPTS

GUARD = SKILL_SCRIPTS / "git_guard.py"

# Each guarded base command with a word its reason must carry (design D4).
GUARDED = (
    ("gh pr merge 5 --squash", "person merges"),
    ("gh repo delete x --yes", "person"),
    ("git push origin main", "PR"),
    ("git push origin HEAD:main", "PR"),
    ("git push origin x:refs/heads/main", "PR"),
    ("git push --force", "commit on top"),
    ("git push -fu origin b", "commit on top"),
    ("git push --force-with-lease", "commit on top"),
    ("git push --force-with-lease=main:abc origin b", "commit on top"),
    ("git push --force-if-includes", "commit on top"),
    ("git push origin +b", "commit on top"),
    ("git push --no-verify", "hook reports"),
    ("git commit --no-verify -m x", "hook reports"),
    ("git commit -nm x", "hook reports"),
    ("git reset --hard HEAD~1", "stash"),
    ("git branch -D b", "branch -d"),
    ("git branch --delete --force b", "branch -d"),
)

GIT_GLOBAL_OPTIONS = ("-C .", "-c a=b", "--git-dir=.git")
GH_GLOBAL_OPTIONS = ("-R o/r", "--repo o/r", "--repo=o/r")


def _forms(command: str) -> list[str]:
    """`command` alone and in every form the guard must see through."""
    forms = [
        command,
        f"cd x && {command}",
        f"true; {command}",
        f"true | {command}",
        f"sh -c {shlex.quote(command)}",
        f"bash --rcfile /dev/null -c {shlex.quote(command)}",
        f"bash -o pipefail -c {shlex.quote(command)}",
        f"timeout 5 {command}",
        f"A=1 {command}",
        f"env A=1 {command}",
    ]
    tool, _, rest = command.partition(" ")
    options = GIT_GLOBAL_OPTIONS if tool == "git" else GH_GLOBAL_OPTIONS
    return forms + [f"{tool} {option} {rest}" for option in options]


def _guard(stdin: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(GUARD), *args],
        input=stdin,
        capture_output=True,
        encoding="utf-8",
        check=False,
    )


def _pre_bash(command: str) -> subprocess.CompletedProcess:
    return _guard(json.dumps({"tool_input": {"command": command}}), "pre-bash")


@pytest.mark.parametrize(
    ("command", "word"),
    [(form, word) for base, word in GUARDED for form in _forms(base)],
)
def test_guarded_command_is_denied_with_the_alternative(command: str, word: str) -> None:
    result = _pre_bash(command)
    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)["hookSpecificOutput"]
    assert output["hookEventName"] == "PreToolUse"
    assert output["permissionDecision"] == "deny"
    assert word in output["permissionDecisionReason"]


@pytest.mark.parametrize(
    ("command", "word"),
    [
        (form.format(shlex.quote(base)), word)
        for base, word in GUARDED
        for form in ("bash -lc {}", "sh -ec {}", "bash -c -e {}")
    ],
)
def test_clustered_shell_flag_is_unwrapped(command: str, word: str) -> None:
    result = _pre_bash(command)
    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)["hookSpecificOutput"]
    assert output["permissionDecision"] == "deny"
    assert word in output["permissionDecisionReason"]


@pytest.mark.parametrize(
    "command",
    (
        "echo 'x",
        "git push -u origin feature",
        "git push origin HEAD",
        "git branch -d feature",
        "git reset --soft HEAD~1",
        'git commit -m "skip --no-verify"',
        "gh pr view 1",
        "git push -n origin b",
        "git branch -d -- -D",
        'echo "gh pr merge"',
    ),
)
def test_ordinary_command_is_silent(command: str) -> None:
    result = _pre_bash(command)
    assert (result.returncode, result.stdout, result.stderr) == (0, "", "")


@pytest.mark.parametrize("stdin", ("{}", ""))
def test_malformed_payload_is_silent(stdin: str) -> None:
    result = _guard(stdin, "pre-bash")
    assert (result.returncode, result.stdout, result.stderr) == (0, "", "")


def test_unparsed_git_command_is_a_visible_hook_error() -> None:
    """A heredoc body with an apostrophe defeats the lexer: the call proceeds (exit 1 does not
    block) and the hook error says the command was not checked (design D6)."""
    result = _pre_bash("git commit -F - <<'EOF'\ndon't\nEOF")
    assert result.returncode == 1
    assert result.stdout == ""
    assert "not checked" in result.stderr


@pytest.mark.parametrize("args", ((), ("pre-read",)))
def test_unknown_subcommand_is_a_visible_non_blocking_error(args: tuple[str, ...]) -> None:
    """Exit 2 behind a `Bash` matcher would deny every call; exit 1 is a visible hook error."""
    result = _guard("{}", *args)
    assert result.returncode == 1
    assert "usage" in result.stderr


def test_no_static_deny_shadows_the_guard() -> None:
    """A matching `permissions.deny` rule blocks before the hook runs, so the guard's
    alternative would never reach the agent."""
    settings = json.loads((ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
    patterns = [str(p) for p in settings["permissions"]["deny"]]
    guarded = re.compile(r"Bash\((?:git (?:push|commit|reset|branch)|gh (?:pr merge|repo delete))")
    shadowing = [pattern for pattern in patterns if guarded.match(pattern)]
    assert not shadowing, f"deny entries shadow the git guard: {shadowing}"
    assert "Bash(sleep:*)" in patterns
